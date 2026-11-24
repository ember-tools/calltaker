"""Complaints a caller can describe: what the person feels, or what someone beside them sees.

The catalogue lives in `daten/beschwerden/`, one entry per situation (Lage): the protocols it
covers, a list in the person's own words (`selbst`) and a list in the words of someone beside them
(`beobachtet`). What a caller says decides the trainee's answers, so nothing drawn may contradict
the scenario's own path or opening. A situation and each complaint can be narrowed: to codes
starting with given prefixes (`codes`), to paths whose text matches every pattern of `wenn` and
none of `nicht`, and a situation to an age range. A complaint can also name what it shows
(`zeigt`): a clouded mind, shortness of breath, or a person awake and talking; it is left out where
the opening says otherwise. Texts about the person use `{Er}`, `{er}`, `{ihn}` and `{ihm}`, filled
in for the person's sex. The server checks the catalogue against the graph when it starts.
"""

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from abfrage import Abfragegraph, Endpunkt
from meldehand import WACH
from stimmigkeit import pfadtext

PRONOMEN = {"Er": "Sie", "er": "sie", "ihn": "sie", "ihm": "ihr"}
PLATZHALTER = re.compile(r"\{(\w+)\}")
NORMALE_ATMUNG = "ja-normale-atmung"
Zeichen = Literal["eingetruebt", "atemnot", "wach"]


class Modell(BaseModel):
    """Base of the catalogue models: camel case on the wire, unknown fields refused."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Eingrenzung(Modell):
    """Which end points something fits: code prefixes and patterns on the path's text."""

    codes: list[str] = Field(default_factory=list)
    wenn: list[str] = Field(default_factory=list)
    nicht: list[str] = Field(default_factory=list)

    def passt(self, endpunkt: Endpunkt, text: str) -> bool:
        """Tell whether an end point with this path text is covered."""
        return (
            (not self.codes or endpunkt.code.startswith(tuple(self.codes)))
            and all(re.search(muster, text) for muster in self.wenn)
            and not any(re.search(muster, text) for muster in self.nicht)
        )


class Beschwerde(Eingrenzung):
    """One complaint, the end points it fits and what it shows of the person's state."""

    text: str
    zeigt: list[Zeichen] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def aus_text(cls, wert: object) -> object:
        """Accept a bare text for a complaint that fits everywhere in its situation."""
        return {"text": wert} if isinstance(wert, str) else wert

    def stimmt(self, reaktion: str | None, atmung: str | None) -> bool:
        """Tell whether the complaint agrees with the opening's reaction and breathing."""
        if "eingetruebt" in self.zeigt and reaktion == WACH:
            return False
        if "wach" in self.zeigt and reaktion not in (None, WACH):
            return False
        return not ("atemnot" in self.zeigt and atmung == NORMALE_ATMUNG)


class Lage(Eingrenzung):
    """The complaints of one situation, in the person's own view and in an onlooker's."""

    id: str
    protokolle: list[str]
    alter: tuple[int, int] = (0, 120)
    selbst: list[Beschwerde]
    beobachtet: list[Beschwerde]

    def deckt(self, endpunkt: Endpunkt, text: str, alter: int) -> bool:
        """Tell whether the situation covers an end point for a person of this age."""
        von, bis = self.alter
        return (
            endpunkt.protokoll in self.protokolle
            and von <= alter <= bis
            and self.passt(endpunkt, text)
        )


class Katalog(Modell):
    """One file of situations."""

    lagen: list[Lage]


def laden(verzeichnis: Path, graph: Abfragegraph) -> list[Lage]:
    """Read every catalogue file of a folder and check it against the graph, naming every fault."""
    lagen = []
    for datei in sorted(verzeichnis.glob("*.json")):
        try:
            katalog = Katalog.model_validate(json.loads(datei.read_text("utf-8")))
        except ValueError as fehler:
            raise ValueError(f"{datei.name}: {fehler}") from fehler
        lagen.extend(katalog.lagen)
    fehler = katalogfehler(lagen, graph)
    if fehler:
        raise ValueError("Beschwerden fehlerhaft:\n" + "\n".join(fehler))
    return lagen


def katalogfehler(lagen: list[Lage], graph: Abfragegraph) -> list[str]:
    """Return unknown protocols, codes and patterns, repeated ids, empty entries, bad placeholders.

    A code prefix or pattern must fit at least one path of the situation's protocols, so a typo
    cannot quietly switch a complaint off.
    """
    ids = [lage.id for lage in lagen]
    fehler = [f"{id_}: gibt es doppelt" for id_ in sorted({i for i in ids if ids.count(i) > 1})]
    protokolle = {endpunkt.protokoll for endpunkt in graph.endpunkte}
    for lage in lagen:
        if not lage.protokolle:
            fehler.append(f"{lage.id}: ohne Protokoll")
        fehler.extend(
            f"{lage.id}: Protokoll {protokoll} gibt es nicht"
            for protokoll in lage.protokolle
            if protokoll not in protokolle
        )
        pfade = [
            (endpunkt, pfadtext(graph, endpunkt))
            for endpunkt in graph.endpunkte
            if endpunkt.protokoll in lage.protokolle
        ]
        if not lage.selbst and not lage.beobachtet:
            fehler.append(f"{lage.id}: ohne Beschwerden")
        for teil, name in [(lage, lage.id)] + [
            (b, f"{lage.id} „{b.text}“") for b in [*lage.selbst, *lage.beobachtet]
        ]:
            fehler.extend(eingrenzungsfehler(teil, name, pfade))
        fehler.extend(
            f"{lage.id}: unbekannter Platzhalter {{{platz}}} in „{b.text}“"
            for b in [*lage.selbst, *lage.beobachtet]
            for platz in PLATZHALTER.findall(b.text)
            if platz not in PRONOMEN
        )
    return fehler


def eingrenzungsfehler(
    teil: Eingrenzung, name: str, pfade: list[tuple[Endpunkt, str]]
) -> list[str]:
    """Return the code prefixes and patterns of one part that fit no path, or do not compile."""
    fehler = [
        f"{name}: kein Code beginnt mit {code}"
        for code in teil.codes
        if not any(endpunkt.code.startswith(code) for endpunkt, _ in pfade)
    ]
    for muster in [*teil.wenn, *teil.nicht]:
        try:
            ausdruck = re.compile(muster)
        except re.error:
            fehler.append(f"{name}: Muster {muster} ist ungültig")
            continue
        if not any(ausdruck.search(text) for _, text in pfade):
            fehler.append(f"{name}: Muster {muster} passt auf keinen Pfad")
    return fehler


def lage_fuer(lagen: list[Lage], endpunkt: Endpunkt, text: str, alter: int) -> Lage | None:
    """Return the situation covering an end point, one narrowed by codes before a whole protocol."""
    passende = [lage for lage in lagen if lage.deckt(endpunkt, text, alter)]
    passende.sort(key=lambda lage: not lage.codes)
    return passende[0] if passende else None


def gefuellt(text: str, weiblich: bool) -> str:
    """Return a complaint with its pronouns filled in for the person's sex."""
    return PLATZHALTER.sub(lambda treffer: PRONOMEN[treffer[1]] if weiblich else treffer[1], text)
