"""Instructions to the caller: what the call-taker tells them to do until help arrives.

The catalogue lives in its own files under `daten/anleitungen/`, apart from the question graph,
so its texts can be kept without touching the graph. Each instruction says when it is due: a list
of alternatives, each a set of conditions on the questioning that must all hold. An alternative
holds when the Fachrichtung matches, a protocol of `protokolle` was chosen, every answer of
`antworten` was given, none of `nicht` was given and the result's category starts with one of
`kategorien` and with none of `nicht_kategorien`; conditions left out do not count. An
instruction is not due while the caller is not on site, as the graph's `abwesend` answers tell,
unless it is marked `auch_ohne_vor_ort`.
Which instructions are due is worked out in the browser from the trainee's path, by the same
rules; the server only checks the catalogue against the graph when it starts.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from abfrage import Abfragegraph, Gegebene


class Modell(BaseModel):
    """Base of the catalogue models: camel case on the wire, unknown fields refused."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Wenn(Modell):
    """One set of conditions that together make an instruction due."""

    fachrichtung: str | None = None
    protokolle: list[str] = Field(default_factory=list)
    antworten: list[Gegebene] = Field(default_factory=list)
    nicht: list[Gegebene] = Field(default_factory=list)
    kategorien: list[str] = Field(default_factory=list)
    nicht_kategorien: list[str] = Field(default_factory=list)

    def leer(self) -> bool:
        """Tell whether the set names no condition at all, and so would always hold."""
        return not (self.fachrichtung or self.protokolle or self.antworten or self.kategorien)


class Anleitung(Modell):
    """One instruction: its sentences to read out, whether it must be given, and when it is due."""

    id: str
    titel: str
    saetze: list[str]
    pflicht: bool = False
    wenn: list[Wenn]
    schliesst_aus: list[str] = Field(default_factory=list)
    auch_ohne_vor_ort: bool = False
    quelle: str


class Katalog(Modell):
    """One file of instructions."""

    anleitungen: list[Anleitung]


def laden(verzeichnis: Path, graph: Abfragegraph) -> list[Anleitung]:
    """Read every catalogue file of a folder and check it against the graph, naming every fault."""
    anleitungen = []
    for datei in sorted(verzeichnis.glob("*.json")):
        try:
            katalog = Katalog.model_validate(json.loads(datei.read_text("utf-8")))
        except ValueError as fehler:
            raise ValueError(f"{datei.name}: {fehler}") from fehler
        anleitungen.extend(katalog.anleitungen)
    fehler = katalogfehler(anleitungen, graph)
    if fehler:
        raise ValueError("Anleitungen fehlerhaft:\n" + "\n".join(fehler))
    return anleitungen


def katalogfehler(anleitungen: list[Anleitung], graph: Abfragegraph) -> list[str]:
    """Return what in the catalogue the graph does not know, and repeated or dangling ids."""
    ids = [anleitung.id for anleitung in anleitungen]
    fehler = [f"{id_}: gibt es doppelt" for id_ in sorted({i for i in ids if ids.count(i) > 1})]
    wurzel = graph.knoten[graph.meta.wurzel]
    fachrichtungen = {antwort.id for antwort in wurzel.antworten or []}
    protokolle = {
        antwort.protokoll
        for knoten in graph.knoten.values()
        for antwort in knoten.antworten or []
        if antwort.protokoll
    }
    kategorien = {endpunkt.kategorie for endpunkt in graph.endpunkte}
    for anleitung in anleitungen:
        if not anleitung.wenn or any(wenn.leer() for wenn in anleitung.wenn):
            fehler.append(f"{anleitung.id}: ohne Bedingung")
        if anleitung.id in anleitung.schliesst_aus:
            fehler.append(f"{anleitung.id}: schließt sich selbst aus")
        for wenn in anleitung.wenn:
            if wenn.fachrichtung and wenn.fachrichtung not in fachrichtungen:
                fehler.append(f"{anleitung.id}: Fachrichtung {wenn.fachrichtung} gibt es nicht")
            fehler.extend(
                f"{anleitung.id}: Protokoll {protokoll} gibt es nicht"
                for protokoll in wenn.protokolle
                if protokoll not in protokolle
            )
            fehler.extend(
                f"{anleitung.id}: Antwort {gegeben.antwort} an {gegeben.knoten} gibt es nicht"
                for gegeben in [*wenn.antworten, *wenn.nicht]
                if graph.antwort(gegeben.knoten, gegeben.antwort) is None
            )
            fehler.extend(
                f"{anleitung.id}: keine Kategorie beginnt mit {kategorie}"
                for kategorie in [*wenn.kategorien, *wenn.nicht_kategorien]
                if not any(k.startswith(kategorie) for k in kategorien)
            )
        fehler.extend(
            f"{anleitung.id}: schließt {anderes} aus, das es nicht gibt"
            for anderes in anleitung.schliesst_aus
            if anderes not in ids
        )
    return fehler


def nach_aussen(anleitungen: list[Anleitung]) -> list[dict]:
    """Return the catalogue as the frontend reads it."""
    return [anleitung.model_dump(by_alias=True, exclude_defaults=True) for anleitung in anleitungen]
