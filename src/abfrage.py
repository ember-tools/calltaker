"""The question graph: its format, loading it from its files, checking it and indexing its codes.

The graph lives as JSON files below one folder, each holding a `knoten` object of nodes by id,
plus a `meta.json` with the version, the root and the notes on where the data comes from. A node
is exactly one of four kinds:

* a question with answers to choose from (`frage` + `antworten`),
* a question answered by typing (`frage` + `eingabe` + `ziel`),
* a switch that asks nothing and follows the answer given earlier at another node (`weiche`),
* an endpoint carrying a dispatch code (`code`).
"""

import re
from collections import deque
from functools import cached_property
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

ID_MUSTER = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class Modell(BaseModel):
    """Base of the graph's models: unknown fields are refused, so a typo in a file is found."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Altersgrenze(Modell):
    """The ages an answer applies to, both bounds inclusive, or that it is for an unknown age."""

    min: int | None = None
    max: int | None = None
    unbekannt: bool = False


class Antwort(Modell):
    """One answer to choose from."""

    id: str
    label: str
    aussage: str = ""
    ziel: str
    nr: str | None = None
    farbe: str | None = None
    protokoll: str | None = None
    alter: Altersgrenze | None = None
    geschlecht: Literal["w", "m"] | None = None


class Leer(Modell):
    """What is recorded when a typed answer is left empty."""

    label: str
    aussage: str


class Eingabe(Modell):
    """A question answered by typing; `{wert}` in the template stands for what was typed."""

    vorlage: str
    platzhalter: str
    leer: Leer | None = None


class Weiche(Modell):
    """A switch following the answer given at another node."""

    knoten: str
    ziele: dict[str, str]


class Knoten(Modell):
    """One node of the graph; which fields are set decides its kind."""

    frage: str | None = None
    hinweis: str | None = None
    pflicht: bool = False
    anleitung: str | None = None
    antworten: list[Antwort] | None = None
    eingabe: Eingabe | None = None
    ziel: str | None = None
    weiche: Weiche | None = None
    code: str | None = None
    kategorie: str | None = None
    anlass: str | None = None
    stichwort: str | None = None

    @model_validator(mode="after")
    def genau_eine_art(self) -> Self:
        """Refuse a node that is not exactly one of the four kinds."""
        arten = [
            self.antworten is not None,
            self.eingabe is not None,
            self.weiche is not None,
            self.code is not None,
        ]
        if sum(arten) != 1:
            raise ValueError("ein Knoten ist genau Auswahl, Eingabe, Weiche oder Endpunkt")
        if self.antworten is not None and (not self.frage or not self.antworten or self.ziel):
            raise ValueError("eine Auswahl braucht Frage und Antworten, aber kein Ziel")
        if self.eingabe is not None and (not self.frage or not self.ziel):
            raise ValueError("eine Eingabe braucht Frage und Ziel")
        if self.weiche is not None and (self.frage or self.ziel):
            raise ValueError("eine Weiche fragt nichts und hat kein eigenes Ziel")
        if self.code is not None and (self.frage or self.ziel):
            raise ValueError("ein Endpunkt fragt nichts und führt nirgends hin")
        return self

    def nachfolger(self) -> list[str]:
        """Return the ids this node leads to."""
        if self.antworten is not None:
            return [antwort.ziel for antwort in self.antworten]
        if self.weiche is not None:
            return list(self.weiche.ziele.values())
        return [self.ziel] if self.ziel else []


class Bedingung(Modell):
    """An answer given earlier: one of these answers at that node."""

    knoten: str
    antworten: list[str]


class Eingrenzung(Modell):
    """Which answers of a node come first when earlier answers point that way.

    `zuerst` names answers of the node by their id or by the protocol they choose, in the order
    they are shown; the rest of the node's answers follow under "weitere".
    """

    knoten: str
    wenn: list[Bedingung]
    zuerst: list[str]


class Person(Modell):
    """Where the opening asks for the person, so later answers that depend on it can follow.

    `geschlecht` maps the answers of `geschlecht_knoten` to "w" and "m".
    """

    alter_knoten: str
    geschlecht_knoten: str
    geschlecht: dict[str, Literal["w", "m"]]


class Meta(Modell):
    """The graph's version, its root, the notes on its data, and how the questioning narrows."""

    version: int
    wurzel: str
    quelle: str
    hinweise: dict[str, str] = Field(default_factory=dict)
    notfallkategorien: dict[str, str] = Field(default_factory=dict)
    person: Person | None = None
    eingrenzung: list[Eingrenzung] = Field(default_factory=list)


class Schritt(Modell):
    """One step of a path through the graph: the node and the answer taken there."""

    knoten: str
    antwort: str | None = None


class Endpunkt(Modell):
    """A code with one path that reaches it from its protocol's choice."""

    code: str
    kategorie: str
    anlass: str
    stichwort: str
    fachrichtung: str
    protokoll: str
    knoten: str
    pfad: list[Schritt]


class Abfragegraph(BaseModel):
    """The whole graph, checked on construction."""

    model_config = ConfigDict(frozen=True)

    meta: Meta
    knoten: dict[str, Knoten]

    @model_validator(mode="after")
    def pruefen(self) -> Self:
        """Refuse a graph whose structure is broken, naming every fault found."""
        fehler = strukturfehler(self)
        if fehler:
            raise ValueError("\n".join(fehler))
        return self

    @cached_property
    def tiefen(self) -> dict[str, int]:
        """Return how many steps each node lies from the root at the fewest."""
        return tiefen(self)

    @cached_property
    def endpunkte(self) -> list[Endpunkt]:
        """Every endpoint, once per protocol that reaches it, with the first path found to it."""
        return endpunkte(self)

    def antwort(self, knoten: str, antwort: str) -> Antwort | None:
        """Return the answer with the given id at a node, if both exist."""
        eintrag = self.knoten.get(knoten)
        for kandidat in (eintrag.antworten or []) if eintrag else []:
            if kandidat.id == antwort:
                return kandidat
        return None

    def buendel(self) -> dict:
        """Return the graph as the frontend loads it: meta, nodes and the code index."""
        return {
            "meta": self.meta.model_dump(),
            "knoten": {
                id_: knoten.model_dump(exclude_none=True, exclude_defaults=True)
                for id_, knoten in self.knoten.items()
            },
            "endpunkte": [endpunkt.model_dump(exclude_none=True) for endpunkt in self.endpunkte],
        }


class Datei(Modell):
    """One file of nodes."""

    knoten: dict[str, dict]


def laden(verzeichnis: Path) -> Abfragegraph:
    """Read and check the graph from its folder, naming the file and node of every fault."""
    meta_datei = verzeichnis / "meta.json"
    meta = lesen(meta_datei, verzeichnis, Meta)
    knoten: dict[str, Knoten] = {}
    for datei in sorted(verzeichnis.rglob("*.json")):
        if datei == meta_datei:
            continue
        name = datei.relative_to(verzeichnis)
        for id_, roh in lesen(datei, verzeichnis, Datei).knoten.items():
            if id_ in knoten:
                raise ValueError(f"{name}: Knoten {id_} gibt es doppelt")
            try:
                knoten[id_] = Knoten.model_validate(roh)
            except ValidationError as fehler:
                raise ValueError(f"{name}: {id_}: {kurz(fehler)}") from fehler
    return Abfragegraph(meta=meta, knoten=knoten)


def lesen[T: BaseModel](datei: Path, verzeichnis: Path, modell: type[T]) -> T:
    """Read one file as the given model, naming the file when it is not valid."""
    name = datei.relative_to(verzeichnis)
    try:
        return modell.model_validate_json(datei.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as fehler:
        text = kurz(fehler) if isinstance(fehler, ValidationError) else str(fehler)
        raise ValueError(f"{name}: {text}") from fehler


def kurz(fehler: ValidationError) -> str:
    """Return a validation error as one line per fault, with where it sits."""
    return "; ".join(
        f"{'.'.join(str(teil) for teil in eintrag['loc']) or 'Knoten'}: {eintrag['msg']}"
        for eintrag in fehler.errors()
    )


def strukturfehler(graph: Abfragegraph) -> list[str]:
    """Return every structural fault of a graph, empty when there is none."""
    fehler = [*idfehler(graph), *zielfehler(graph), *weichenfehler(graph)]
    if fehler:
        return fehler
    fehler = [*zyklusfehler(graph), *erreichbarkeitsfehler(graph)]
    if fehler:
        return fehler
    return [*weichenfolgefehler(graph), *eingrenzungsfehler(graph)]


def eingrenzungsfehler(graph: Abfragegraph) -> list[str]:
    """Return the narrowing rules and person nodes that name nodes or answers the graph lacks."""
    fehler = []
    person = graph.meta.person
    if person is not None:
        for id_ in (person.alter_knoten, person.geschlecht_knoten):
            if id_ not in graph.knoten:
                fehler.append(f"Person: Knoten {id_} gibt es nicht")
        fehler.extend(
            f"Person: Antwort {antwort} gibt es nicht"
            for antwort in person.geschlecht
            if graph.antwort(person.geschlecht_knoten, antwort) is None
        )
    for regel in graph.meta.eingrenzung:
        knoten = graph.knoten.get(regel.knoten)
        if knoten is None or not knoten.antworten:
            fehler.append(f"Eingrenzung: {regel.knoten} ist keine Auswahl")
            continue
        namen = {a.id for a in knoten.antworten} | {a.protokoll for a in knoten.antworten}
        fehler.extend(
            f"Eingrenzung {regel.knoten}: {name} gibt es dort nicht"
            for name in regel.zuerst
            if name not in namen
        )
        fehler.extend(
            f"Eingrenzung {regel.knoten}: Bedingung {antwort} an {bedingung.knoten} gibt es nicht"
            for bedingung in regel.wenn
            for antwort in bedingung.antworten
            if graph.antwort(bedingung.knoten, antwort) is None
        )
    return fehler


def idfehler(graph: Abfragegraph) -> list[str]:
    """Return the ids that break the id pattern or repeat within a node or across protocols."""
    fehler = [
        f"Knoten-ID {id_} passt nicht zum Muster"
        for id_ in graph.knoten
        if not ID_MUSTER.match(id_)
    ]
    wahlen: dict[str, list[tuple[str, str]]] = {}
    for id_, knoten in graph.knoten.items():
        gesehen: set[str] = set()
        for antwort in knoten.antworten or []:
            if not ID_MUSTER.match(antwort.id):
                fehler.append(f"{id_}: Antwort-ID {antwort.id} passt nicht zum Muster")
            if antwort.id in gesehen:
                fehler.append(f"{id_}: Antwort-ID {antwort.id} doppelt")
            gesehen.add(antwort.id)
            if antwort.protokoll:
                wahlen.setdefault(antwort.protokoll, []).append((id_, antwort.ziel))
                fehler.extend(protokollfehler(graph, id_, antwort.protokoll))
    for protokoll, orte in wahlen.items():
        if len(orte) > 1:
            fehler.extend(
                f"{id_}: Protokoll {protokoll} wird mehrfach gewählt, "
                "führt hier aber nicht in seine eigenen Knoten"
                for id_, ziel in orte
                if not ziel.startswith(f"{protokoll}.")
            )
    return fehler


def protokollfehler(graph: Abfragegraph, id_: str, protokoll: str) -> list[str]:
    """Return what is wrong with a protocol id: its pattern, or a Fachrichtung not at the root."""
    if not ID_MUSTER.match(protokoll):
        return [f"{id_}: Protokoll-ID {protokoll} passt nicht zum Muster"]
    wurzel = graph.knoten.get(graph.meta.wurzel)
    fachrichtungen = {antwort.id for antwort in (wurzel.antworten or [])} if wurzel else set()
    fachrichtung = fachrichtung_von(protokoll)
    if fachrichtung not in fachrichtungen:
        return [f"{id_}: Protokoll {protokoll} gehört zu keiner Fachrichtung der Wurzel"]
    return []


def zielfehler(graph: Abfragegraph) -> list[str]:
    """Return every target that names no node."""
    fehler = []
    if graph.meta.wurzel not in graph.knoten:
        fehler.append(f"Wurzel {graph.meta.wurzel} gibt es nicht")
    for id_, knoten in graph.knoten.items():
        fehler.extend(
            f"{id_}: Ziel {ziel} gibt es nicht"
            for ziel in knoten.nachfolger()
            if ziel not in graph.knoten
        )
    return fehler


def weichenfehler(graph: Abfragegraph) -> list[str]:
    """Return every switch that does not cover exactly the answers of the node it follows."""
    fehler = []
    for id_, knoten in graph.knoten.items():
        if knoten.weiche is None:
            continue
        bezug = graph.knoten.get(knoten.weiche.knoten)
        if bezug is None or bezug.antworten is None:
            fehler.append(f"{id_}: Weiche folgt {knoten.weiche.knoten}, das keine Auswahl ist")
            continue
        erwartet = {antwort.id for antwort in bezug.antworten}
        if set(knoten.weiche.ziele) != erwartet:
            fehler.append(
                f"{id_}: Weiche deckt nicht genau die Antworten von {knoten.weiche.knoten} ab"
            )
    return fehler


def zyklusfehler(graph: Abfragegraph) -> list[str]:
    """Return a fault for every node that lies on a cycle."""
    eingang = {id_: 0 for id_ in graph.knoten}
    for knoten in graph.knoten.values():
        for ziel in knoten.nachfolger():
            eingang[ziel] += 1
    offen = deque(id_ for id_, anzahl in eingang.items() if anzahl == 0)
    while offen:
        for ziel in graph.knoten[offen.popleft()].nachfolger():
            eingang[ziel] -= 1
            if eingang[ziel] == 0:
                offen.append(ziel)
    return [f"{id_} liegt auf einem Zyklus" for id_, anzahl in eingang.items() if anzahl > 0]


def erreichbarkeitsfehler(graph: Abfragegraph) -> list[str]:
    """Return a fault for every node the root does not reach."""
    erreicht = {graph.meta.wurzel}
    offen = deque([graph.meta.wurzel])
    while offen:
        for ziel in graph.knoten[offen.popleft()].nachfolger():
            if ziel not in erreicht:
                erreicht.add(ziel)
                offen.append(ziel)
    return [
        f"{id_} ist von der Wurzel aus nicht erreichbar"
        for id_ in graph.knoten
        if id_ not in erreicht
    ]


def weichenfolgefehler(graph: Abfragegraph) -> list[str]:
    """Return a fault for every switch reachable on a path that skips the node it follows."""
    return [
        f"{id_}: Weiche ist erreichbar, ohne dass {knoten.weiche.knoten} gefragt wurde"
        for id_, knoten in graph.knoten.items()
        if knoten.weiche is not None and id_ in erreichbar_ohne(graph, knoten.weiche.knoten)
    ]


def erreichbar_ohne(graph: Abfragegraph, ausgelassen: str) -> set[str]:
    """Return the nodes the root reaches when one node is taken out of the graph."""
    if graph.meta.wurzel == ausgelassen:
        return set()
    erreicht = {graph.meta.wurzel}
    offen = deque([graph.meta.wurzel])
    while offen:
        for ziel in graph.knoten[offen.popleft()].nachfolger():
            if ziel != ausgelassen and ziel not in erreicht:
                erreicht.add(ziel)
                offen.append(ziel)
    return erreicht


def endpunkte(graph: Abfragegraph) -> list[Endpunkt]:
    """Index every endpoint once per protocol, with the shortest way to it from the root.

    Several endpoints of one protocol may share a code and differ in category or reason, the
    child's variant of a determinant for instance, so endpoints are indexed by node, not by code.
    A protocol can be chosen in more than one place: cardiac arrest from the main complaints and,
    straight away, from "atmet nicht" in the opening. Each endpoint keeps the path whose whole way
    from the root is shortest, which is the one a call takes.
    """
    tiefe = graph.tiefen
    kuerzeste: dict[tuple[str, str], Endpunkt] = {}
    for id_, knoten in graph.knoten.items():
        for antwort in knoten.antworten or []:
            if antwort.protokoll:
                for gefunden in protokollendpunkte(graph, id_, antwort):
                    schluessel = (gefunden.protokoll, gefunden.knoten)
                    bisher = kuerzeste.get(schluessel)
                    if bisher is None or weg(tiefe, gefunden) < weg(tiefe, bisher):
                        kuerzeste[schluessel] = gefunden
    return list(kuerzeste.values())


def weg(tiefe: dict[str, int], endpunkt: Endpunkt) -> int:
    """Return the steps from the root to an endpoint along its indexed path."""
    return tiefe.get(endpunkt.pfad[0].knoten, len(tiefe)) + len(endpunkt.pfad)


def tiefen(graph: Abfragegraph) -> dict[str, int]:
    """Return each node's fewest steps from the root, walking every answer, input and switch."""
    tiefe = {graph.meta.wurzel: 0}
    offen = deque([graph.meta.wurzel])
    while offen:
        id_ = offen.popleft()
        for ziel in graph.knoten[id_].nachfolger():
            if ziel not in tiefe:
                tiefe[ziel] = tiefe[id_] + 1
                offen.append(ziel)
    return tiefe


def fachrichtung_von(protokoll: str) -> str:
    """Return the root answer a protocol belongs to: rd, or brand and th for the fire brigade's.

    Fire and technical rescue protocols share the prefix fw, as the fire brigade answers both,
    but each has its own start at the root.
    """
    teile = protokoll.split(".")
    return teile[1] if teile[0] == "fw" and len(teile) > 2 else teile[0]


def protokollendpunkte(graph: Abfragegraph, wahl: str, antwort: Antwort) -> list[Endpunkt]:
    """Return the codes of one protocol, walking breadth first from the answer that chose it."""
    fachrichtung = fachrichtung_von(antwort.protokoll)
    gesehen: set[str] = set()
    gefunden = []
    offen = deque([(antwort.ziel, [Schritt(knoten=wahl, antwort=antwort.id)])])
    while offen:
        id_, pfad = offen.popleft()
        if id_ in gesehen:
            continue
        gesehen.add(id_)
        knoten = graph.knoten[id_]
        if knoten.code is not None:
            gefunden.append(endpunkt(knoten, id_, fachrichtung, antwort.protokoll, pfad))
            continue
        for schritt, ziel in schritte(knoten, id_):
            offen.append((ziel, [*pfad, schritt]))
    return gefunden


def schritte(knoten: Knoten, id_: str) -> list[tuple[Schritt, str]]:
    """Return the steps leaving a node, each with the node it leads to."""
    if knoten.antworten is not None:
        return [
            (Schritt(knoten=id_, antwort=antwort.id), antwort.ziel) for antwort in knoten.antworten
        ]
    if knoten.weiche is not None:
        return [
            (Schritt(knoten=id_, antwort=wert), ziel) for wert, ziel in knoten.weiche.ziele.items()
        ]
    return [(Schritt(knoten=id_), knoten.ziel)]


def endpunkt(knoten: Knoten, id_: str, fachrichtung: str, protokoll: str, pfad: list) -> Endpunkt:
    """Build the index entry of one endpoint."""
    return Endpunkt(
        code=knoten.code,
        kategorie=knoten.kategorie or "",
        anlass=knoten.anlass or "",
        stichwort=knoten.stichwort or "",
        fachrichtung=fachrichtung,
        protokoll=protokoll,
        knoten=id_,
        pfad=pfad,
    )
