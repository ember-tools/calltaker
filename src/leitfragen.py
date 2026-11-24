"""Guidance questions: what the call-taker can ask to find the right tile when unsure.

The catalogue lives in `daten/leitfragen/`, apart from the question graph, and names, per question
node of the graph, an ordered list of guidance questions. Each answer to a guidance question keeps
a subset of the node's tiles (`behaelt`) or takes some out (`nimmt`); an answer with neither, such
as "Weiß nicht", changes nothing. The call-taker is always offered the first question of the list
that still tells the remaining tiles apart, so a flat list behaves like a question tree, its order
being the priority. A safety question (`sicherheit`) is offered first and even when it tells no
tiles apart, since its answer matters for the caller's safety; safety questions stand at the head
of a node's list. A question with `wenn` is offered only while one of those tiles is still in the
running. An answer that would leave no tile, as when the caller contradicts an earlier answer, is
not offered. The questions are gone through in order: each is asked or passed once, and a question
passed is never offered again, since the tiles only shrink. When no question is left, the
remaining tiles, at most `HOECHSTENS_VORGESCHLAGEN`, are the suggestion; the call-taker may pick
any tile directly at any time.
Which question comes next is worked out in the browser by the same rules; the server checks the
catalogue against the graph when it starts, including that every tile can be reached.
"""

import json
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from abfrage import Abfragegraph

HOECHSTENS_VORGESCHLAGEN = 3
HOECHSTENS_ZUSTAENDE = 100_000


class Modell(BaseModel):
    """Base of the catalogue models: camel case on the wire, unknown fields refused."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Leitantwort(Modell):
    """One answer to a guidance question and how it narrows the tiles."""

    label: str
    behaelt: list[str] = Field(default_factory=list)
    nimmt: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def eindeutig(self) -> Self:
        """Refuse an answer that both keeps and takes out tiles."""
        if self.behaelt and self.nimmt:
            raise ValueError(f"„{self.label}“ hat behaelt und nimmt zugleich")
        return self

    def rest(self, kacheln: frozenset[str]) -> frozenset[str]:
        """Return the tiles left after this answer."""
        if self.behaelt:
            return kacheln & set(self.behaelt)
        return kacheln - set(self.nimmt)


class Loesungsbezug(Modell):
    """Where a question that narrows no tile finds its answer in the solution: graph answers.

    The solution's answer at one of the `knoten` that is among `ja` means "Ja", among `nein`
    "Nein"; any other leaves the caller free. One side may stay empty.
    """

    knoten: list[str]
    ja: list[str] = Field(default_factory=list)
    nein: list[str] = Field(default_factory=list)


class Leitfrage(Modell):
    """One guidance question, when it is offered, and its answers.

    A question that narrows no tile, such as a safety question, can name in `loesung` the graph
    answers that settle it, so the solution card can say how the caller answers.
    """

    id: str
    frage: str
    hinweis: str = ""
    sicherheit: bool = False
    wenn: list[str] = Field(default_factory=list)
    antworten: list[Leitantwort]
    loesung: Loesungsbezug | None = None

    def angeboten(self, kacheln: frozenset[str]) -> list[Leitantwort]:
        """Return the answers offered for these remaining tiles: those that leave some tile."""
        return [antwort for antwort in self.antworten if antwort.rest(kacheln)]

    def offen(self, kacheln: frozenset[str]) -> bool:
        """Tell whether the question is offered for these remaining tiles."""
        if self.wenn and not kacheln & set(self.wenn):
            return False
        if self.sicherheit:
            return True
        return len({antwort.rest(kacheln) for antwort in self.angeboten(kacheln)}) > 1


class Knotenleitfragen(Modell):
    """The guidance questions of one graph node, and tiles meant to be picked only directly."""

    knoten: str
    fragen: list[Leitfrage]
    nur_direkt: list[str] = Field(default_factory=list)


class Katalog(Modell):
    """One file of guidance questions."""

    knoten: list[Knotenleitfragen]


def naechste(
    eintrag: Knotenleitfragen, kacheln: frozenset[str], ab: int = 0
) -> tuple[int, Leitfrage] | None:
    """Return the question offered next, from position `ab` on, with its position."""
    for stelle in range(ab, len(eintrag.fragen)):
        if eintrag.fragen[stelle].offen(kacheln):
            return stelle, eintrag.fragen[stelle]
    return None


def erreichbare(eintrag: Knotenleitfragen, alle: frozenset[str]) -> tuple[set[str], bool]:
    """Return the tiles some way through the questions ends with as a suggestion.

    The narrowest answer is followed first, so suggestions turn up early, and a branch whose
    remaining tiles are all known to be reachable already is not followed further, since it
    cannot add any. Past `HOECHSTENS_ZUSTAENDE` states the search gives up: a sound catalogue is
    checked in a few hundred, so that many means some tile cannot be reached. The second value
    tells whether the search finished; if not, the tiles found so far are returned.
    """
    erreicht: set[str] = set()
    gesehen: set[tuple[frozenset[str], int]] = set()
    offen: list[tuple[frozenset[str], int]] = [(alle, 0)]
    while offen:
        kacheln, ab = offen.pop()
        if (kacheln, ab) in gesehen or kacheln <= erreicht:
            continue
        gesehen.add((kacheln, ab))
        if len(gesehen) > HOECHSTENS_ZUSTAENDE:
            return erreicht, False
        gefunden = naechste(eintrag, kacheln, ab)
        if gefunden is None:
            if len(kacheln) <= HOECHSTENS_VORGESCHLAGEN:
                erreicht |= kacheln
            continue
        stelle, frage = gefunden
        reste = sorted((antwort.rest(kacheln) for antwort in frage.angeboten(kacheln)), key=len)
        offen.extend((rest, stelle + 1) for rest in reversed(reste))
    return erreicht, True


def laden(verzeichnis: Path, graph: Abfragegraph) -> list[Knotenleitfragen]:
    """Read every catalogue file of a folder and check it against the graph, naming every fault."""
    eintraege: list[Knotenleitfragen] = []
    for datei in sorted(verzeichnis.glob("*.json")):
        try:
            katalog = Katalog.model_validate(json.loads(datei.read_text("utf-8")))
        except ValueError as fehler:
            raise ValueError(f"{datei.name}: {fehler}") from fehler
        eintraege.extend(katalog.knoten)
    fehler = katalogfehler(eintraege, graph)
    if fehler:
        raise ValueError("Leitfragen fehlerhaft:\n" + "\n".join(fehler))
    return eintraege


def katalogfehler(eintraege: list[Knotenleitfragen], graph: Abfragegraph) -> list[str]:
    """Return unknown nodes and tiles, repeated ids, emptying answers and unreachable tiles."""
    knoten = [eintrag.knoten for eintrag in eintraege]
    fehler = [f"{k}: gibt es doppelt" for k in sorted({k for k in knoten if knoten.count(k) > 1})]
    for eintrag in eintraege:
        graphknoten = graph.knoten.get(eintrag.knoten)
        if graphknoten is None or not graphknoten.antworten:
            fehler.append(f"{eintrag.knoten}: kein Frageknoten im Graphen")
            continue
        kacheln = frozenset(antwort.id for antwort in graphknoten.antworten)
        fehler.extend(knotenfehler(eintrag, kacheln, graph))
    return fehler


def loesungsfehler(name: str, frage: Leitfrage, graph: Abfragegraph) -> list[str]:
    """Return what is wrong with a question's link to the solution.

    Every linked answer must exist at one of the linked nodes, the link must name nodes and
    answers, no answer may stand for both, and the question must offer "Ja" or "Nein" as the link
    answers it.
    """
    bezug = frage.loesung
    if bezug is None:
        return []
    if not bezug.knoten:
        return [f"{name} {frage.id}: Lösung ohne Knoten"]
    fehler = [
        f"{name} {frage.id}: Lösung {antwort} gibt es an {', '.join(bezug.knoten)} nicht"
        for antwort in [*bezug.ja, *bezug.nein]
        if not any(graph.antwort(knoten, antwort) for knoten in bezug.knoten)
    ]
    if not bezug.ja and not bezug.nein:
        fehler.append(f"{name} {frage.id}: Lösung ohne Antworten")
    if set(bezug.ja) & set(bezug.nein):
        fehler.append(f"{name} {frage.id}: Lösung nennt eine Antwort für Ja und Nein")
    labels = {antwort.label for antwort in frage.antworten}
    fehler.extend(
        f"{name} {frage.id}: Lösung braucht die Antwort „{label}“"
        for label, seite in (("Ja", bezug.ja), ("Nein", bezug.nein))
        if seite and label not in labels
    )
    return fehler


def knotenfehler(
    eintrag: Knotenleitfragen, kacheln: frozenset[str], graph: Abfragegraph | None = None
) -> list[str]:
    """Return the faults of the questions at one node with these tiles.

    With the graph, a question's link to the solution is checked as well.
    """
    name = eintrag.knoten
    ids = [frage.id for frage in eintrag.fragen]
    fehler = [f"{name} {i}: gibt es doppelt" for i in sorted({i for i in ids if ids.count(i) > 1})]
    fehler.extend(
        f"{name}: Kachel {kachel} gibt es nicht"
        for kachel in eintrag.nur_direkt
        if kachel not in kacheln
    )
    for frage in eintrag.fragen:
        genannt = [*frage.wenn, *(k for a in frage.antworten for k in [*a.behaelt, *a.nimmt])]
        fehler.extend(
            f"{name} {frage.id}: Kachel {k} gibt es nicht"
            for k in sorted(set(genannt))
            if k not in kacheln
        )
        if len(frage.antworten) < 2:
            fehler.append(f"{name} {frage.id}: weniger als zwei Antworten")
        if graph is not None:
            fehler.extend(loesungsfehler(name, frage, graph))
        labels = [antwort.label for antwort in frage.antworten]
        fehler.extend(
            f"{name} {frage.id}: Antwort „{label}“ gibt es doppelt"
            for label in sorted({label for label in labels if labels.count(label) > 1})
        )
        fehler.extend(
            f"{name} {frage.id}: „{antwort.label}“ lässt keine Kachel übrig"
            for antwort in frage.antworten
            if not antwort.rest(kacheln)
        )
    erste_normale = next(
        (stelle for stelle, frage in enumerate(eintrag.fragen) if not frage.sicherheit),
        len(eintrag.fragen),
    )
    fehler.extend(
        f"{name} {frage.id}: Sicherheitsfrage steht hinter einer anderen Frage"
        for frage in eintrag.fragen[erste_normale:]
        if frage.sicherheit
    )
    erreicht, fertig = erreichbare(eintrag, kacheln)
    fehlend = kacheln - erreicht - set(eintrag.nur_direkt)
    if not fertig:
        return [
            *fehler,
            f"{name}: zu verzweigt, vermutlich nicht erreichbar: {', '.join(sorted(fehlend))}",
        ]
    fehler.extend(
        f"{name}: Kachel {k} ist über die Leitfragen nicht erreichbar" for k in sorted(fehlend)
    )
    return fehler


def nach_aussen(eintraege: list[Knotenleitfragen]) -> list[dict]:
    """Return the catalogue as the frontend reads it."""
    return [eintrag.model_dump(by_alias=True, exclude_defaults=True) for eintrag in eintraege]
