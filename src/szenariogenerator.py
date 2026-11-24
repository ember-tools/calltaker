"""Scenarios made up by the engine: a code, a path that leads there, a place and a caller.

A scenario is drawn in this order:

1. a discipline by weight (medical, fire, technical rescue),
2. a protocol of that discipline with equal chance, then a code of that protocol with equal chance,
   so protocols with many variants of a code do not crowd out the others; codes whose category is
   "Aufwertung entfällt." or empty are never drawn, and a category filter narrows the choice,
3. the opening questions answered to fit the code: who calls and from where, how many people,
   their age and sex, and whether the person reacts and breathes, by a table of rules per
   category, so a resuscitation code never comes with a caller saying the person is awake,
4. a random address from the address list, or a named place when the list is not loaded yet,
5. caller and affected person with made-up names and numbers, the number withheld in 5 % of the
   calls and a different callback number in another 5 %,
6. the caller's mood, weighted by how urgent the code is.

The age is drawn within the age bounds of the answers on the code's path, so a code for children
gets a child.
"""

import math
import random
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from abfrage import Abfragegraph, Antwort, Endpunkt, Knoten
from beziehungen import OBERRAHMEN, beziehung_ziehen
from gefahrstoffe import Stoff, tafel
from generator import festnetznummer, mobilnummer, zufallsname
from geo import METER_JE_GRAD, entfernung
from stimmigkeit import (
    AUTOMATISCH,
    BEIM_BETROFFENEN,
    BESTAETIGT,
    FUER_ANDERE,
    GEHOERT,
    NENNT_SELBST,
    NENNT_SELBST_ODER_DABEI,
    NIEMAND_DA,
    OHNE_SELBST,
    SELBST,
    VOR_ORT_JA,
    WACH,
    pfadtext,
)
from szenario import (
    Adresse,
    Anrufer,
    Betroffener,
    Funkzelle,
    Herkunft,
    OhneAdresse,
    Ort,
    Rolle,
    Szenario,
    Umgebungsort,
    Wahl,
    Ziel,
)

NICHT_ZIEHBAR = {"", "Aufwertung entfällt."}
UNTERDRUECKT_ANTEIL = 0.05
ANDERE_RUECKRUF_ANTEIL = 0.05
ERWACHSEN = (18, 90)
PLATZ_VERSUCHE = 5
TAFEL_UNLESBAR = 0.15
STILLSTAND_PROTOKOLL = "rd.09"
NICHT_VOR_ORT_ANTWORT = {"fw.brand.gebaeudebrand.fluchtweg": "nicht-im-gebaeude"}
GEWICHT_NEUGEBORENE = 0.1
SELTENE_CODES = {"09B01": 0.0526}
VARIANTEN = {"09B01a": 25, "09B01b": 2, "09B01c": 25, "09B01d": 3, "09B01e": 35, "09B01f": 10}
TODESZEICHEN_ALTER = {
    "09B01a": (50, 90),
    "09B01c": (50, 90),
    "09B01e": (50, 90),
    "09B01b": (16, 80),
    "09B01f": (16, 80),
    "09B01d": (18, 90),
}
TODESZEICHEN = "09B01"
LIEGEZEIT = frozenset({"09B01a", "09B01c", "09B01e"})
NEUGEBORENES = "rd.09.09e01-2"
HERGAENGE = (
    ("Hat über Brustschmerzen geklagt und ist dann zusammengesackt.", 45, 90, None),
    ("Lag beim Aufwachen reglos im Bett.", 50, 90, "wohnung"),
    ("Ist ohne Vorwarnung umgefallen.", 16, 90, None),
    ("Ist beim Sport zusammengebrochen.", 16, 60, "draussen"),
    ("Hat sich beim Essen verschluckt und ist blau angelaufen.", 60, 90, None),
    ("Hat sich beim Essen verschluckt und ist blau angelaufen.", 1, 5, None),
    ("Lag plötzlich schlaff und reglos im Bett.", 1, 12, "wohnung"),
    ("Lag morgens reglos im Bettchen und atmet nicht.", 0, 0, "wohnung"),
    ("Hat beim Trinken aufgehört zu atmen und ist blau angelaufen.", 0, 0, None),
    ("Ist beim Spielen plötzlich zusammengebrochen.", 1, 15, None),
    ("Wurde leblos aus dem Wasser gezogen.", 1, 90, "gewaesser"),
    ("Hat an einer Maschine einen Stromschlag bekommen.", 18, 65, "betrieb"),
    ("Ist plötzlich zusammengebrochen.", 1, 90, None),
)
NEUGEBORENEN_HERGAENGE = (
    "Wenige Tage alt, lag nach dem Stillen schlaff und blau im Arm.",
    "Wenige Tage alt, atmet seit eben nicht mehr und ist ganz schlaff.",
)
UMWEGE_SCHLUESSEL = "_nur_ueber_stillstand"
EINSATZORTE = frozenset(
    {
        "Bahnhof",
        "Haltepunkt",
        "Bushaltestelle",
        "Tramhaltestelle",
        "Busbahnhof",
        "Supermarkt",
        "Einkaufszentrum",
        "Kaufhaus",
        "Markt",
        "Schule",
        "Kita",
        "Hochschule",
        "Universität",
        "Park",
        "Spielplatz",
        "Sportanlage",
        "Sporthalle",
        "Sportplatz",
        "Schwimmbad",
        "Hotel",
        "Hostel",
        "Gemeindezentrum",
        "Kirche",
        "Moschee",
        "Museum",
        "Theater",
        "Kino",
        "Bibliothek",
        "Friedhof",
        "Kleingartenanlage",
        "Biergarten",
        "Postfiliale",
        "Pflegeheim",
        "Rathaus",
        "Kulturzentrum",
    }
)
WOHNUNGSPROTOKOLLE = frozenset(
    {
        "fw.brand.gebaeudebrand",
        "fw.brand.rauchentwicklung-brandgeruch",
        "fw.th.tueroeffnung",
        "fw.th.wasserschaden",
        "fw.th.unterstuetzung-rettungsdienst",
    }
)
HAUSTIER_ANTEIL = 0.15
FUNKZELLE_RADIUS = (500.0, 1500.0)
DRAUSSEN_PROTOKOLLE = frozenset(
    {
        "fw.brand.brand-im-freien",
        "fw.th.verkehrsunfall",
        "fw.th.tierrettung",
        "fw.th.person-in-notlage",
    }
)
DRAUSSEN_ARTEN = {
    "Park": "ein Park",
    "Wald": "ein Wald",
    "Gewässer": "am Wasser",
    "Fluss": "am Fluss",
    "Kanal": "am Kanal",
    "Strand": "am Strand",
    "Ufer": "am Ufer",
    "Friedhof": "ein Friedhof",
    "Kleingartenanlage": "eine Kleingartenanlage",
    "Spielplatz": "ein Spielplatz",
    "Sportplatz": "ein Sportplatz",
    "Brunnen": "ein Brunnen auf einem Platz",
}
DRAUSSEN_ARTEN_FUER = {
    "rd": ("Park", "Wald", "Friedhof", "Kleingartenanlage", "Spielplatz", "Sportplatz", "Brunnen"),
    "fw.brand.brand-im-freien": ("Park", "Wald", "Kleingartenanlage", "Friedhof", "Sportplatz"),
    "fw.th.verkehrsunfall": ("Park", "Wald"),
    "fw.th.tierrettung": ("Park", "Wald", "Gewässer", "Friedhof", "Kleingartenanlage"),
    "fw.th.person-in-notlage": ("Park", "Wald", "Gewässer"),
}
DRAUSSEN_VERSATZ = (15.0, 60.0)
UMGEBUNG_RADIUS = 400.0
HIMMELSRICHTUNGEN = (
    "Norden",
    "Nordosten",
    "Osten",
    "Südosten",
    "Süden",
    "Südwesten",
    "Westen",
    "Nordwesten",
)
FUNKZELLE_VERSATZ = (100.0, 800.0)
HAUSTIERE = ("ein Hund", "ein großer Hund", "zwei Katzen", "eine Schlange im Terrarium")
GESCHOSSE = (
    "EG",
    "1. OG",
    "2. OG",
    "3. OG",
    "4. OG",
    "5. OG",
    "Hinterhaus, 2. OG",
    "Seitenflügel, 1. OG",
)


Disziplin = Literal["rd", "brand", "th"]


class Erzeugung(BaseModel):
    """What the trainer sets for made-up scenarios: weights, a category filter and an area."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    gewicht_rd: int = Field(80, ge=0, le=100)
    gewicht_brand: int = Field(12, ge=0, le=100)
    gewicht_th: int = Field(8, ge=0, le=100)
    kategorie: str = Field("", max_length=40)
    protokoll: str = Field("", max_length=80)
    ortsteil: str = Field("", max_length=80)
    bezirk: str = Field("", max_length=80)
    anteil_orte: int = Field(30, ge=0, le=100)
    anteil_ohne_adresse: int = Field(5, ge=0, le=100)

    def gewichte(self) -> dict[Disziplin, int]:
        """Return the weight of each discipline."""
        return {"rd": self.gewicht_rd, "brand": self.gewicht_brand, "th": self.gewicht_th}


class NichtsZuZiehen(ValueError):
    """No code fits the settings, or there is no place to put the scenario."""


@dataclass(frozen=True)
class Quellen:
    """Where places come from: a random address, a random named place, the door nearest a point."""

    adresse: Callable[[random.Random, str, str], dict | None]
    ort: Callable[..., dict | None]
    naechste: Callable[[float, float], dict | None] = lambda *_: None
    umkreis: Callable[[float, float, float], list[dict]] = lambda *_: []
    gefahrstoffe: list[Stoff] = field(default_factory=list)


def disziplin_von(endpunkt: Endpunkt) -> Disziplin:
    """Return the discipline of an endpoint, read from its protocol's id."""
    if endpunkt.protokoll.startswith("fw.brand"):
        return "brand"
    if endpunkt.protokoll.startswith("fw.th"):
        return "th"
    return "rd"


def ziehbare(
    graph: Abfragegraph, erzeugung: Erzeugung
) -> dict[Disziplin, dict[str, list[Endpunkt]]]:
    """Return the endpoints that may be drawn, by discipline and protocol.

    A person who does not breathe is a cardiac arrest whatever else happened, and the questioning
    goes straight there from "atmet nicht". So an arrest is only drawn as such: the endpoints
    reached through that shortcut. Codes of other protocols that would need a person who does not
    breathe are left out; their cause can go into the role notes.
    """
    filter_ = erzeugung.kategorie.strip().lower()
    nach: dict[Disziplin, dict[str, list[Endpunkt]]] = {}
    for endpunkt in graph.endpunkte:
        if endpunkt.kategorie in NICHT_ZIEHBAR or not endpunkt.pfad:
            continue
        if (endpunkt.protokoll, endpunkt.knoten) in nur_ueber_stillstand(graph):
            continue
        if filter_ and not endpunkt.kategorie.lower().startswith(filter_):
            continue
        if erzeugung.protokoll and endpunkt.protokoll != erzeugung.protokoll:
            continue
        nach.setdefault(disziplin_von(endpunkt), {}).setdefault(endpunkt.protokoll, []).append(
            endpunkt
        )
    return nach


def endpunkt_ziehen(graph: Abfragegraph, erzeugung: Erzeugung, zufall: random.Random) -> Endpunkt:
    """Draw a discipline by weight, then a protocol, then a code by `gewichte_der_codes`.

    A chosen protocol overrides the weights: its discipline is drawn whatever its weight.
    """
    nach = ziehbare(graph, erzeugung)
    gewichte = {d: g for d, g in erzeugung.gewichte().items() if g > 0 and d in nach}
    if erzeugung.protokoll:
        gewichte = dict.fromkeys(nach, 1)
    if not gewichte:
        raise NichtsZuZiehen("Kein Code passt zu diesen Einstellungen.")
    disziplin = zufall.choices(list(gewichte), weights=list(gewichte.values()))[0]
    protokoll = zufall.choice(sorted(nach[disziplin]))
    kandidaten = nach[disziplin][protokoll]
    return zufall.choices(kandidaten, weights=gewichte_der_codes(kandidaten))[0]


def gewichte_der_codes(kandidaten: list[Endpunkt]) -> list[float]:
    """Return each endpoint's chance within its protocol: every code once, its variants sharing it.

    A code with variants (09B01a to f for the signs of death; adult, child and newborn of 09E01)
    is drawn as often as a code without, so variants do not crowd out the rest. Newborns get a
    tenth of a variant's share, since they are rare among the calls. Some codes are rare in
    themselves (`SELTENE_CODES`): a person found clearly dead is about one in twenty of those who
    do not breathe. Their variants are weighted by how often each sign is the one reported
    (`VARIANTEN`).
    """
    roh = [
        (GEWICHT_NEUGEBORENE if "NNAD" in e.kategorie else 1.0) * VARIANTEN.get(e.code, 1.0)
        for e in kandidaten
    ]
    summe: dict[str, float] = {}
    for endpunkt, gewicht in zip(kandidaten, roh, strict=True):
        summe[endpunkt.code[:5]] = summe.get(endpunkt.code[:5], 0.0) + gewicht
    return [
        gewicht / summe[endpunkt.code[:5]] * SELTENE_CODES.get(endpunkt.code[:5], 1.0)
        for endpunkt, gewicht in zip(kandidaten, roh, strict=True)
    ]


def altersspanne(graph: Abfragegraph, endpunkt: Endpunkt) -> tuple[int, int]:
    """Return the ages the answers on the code's path allow, adults when they say nothing."""
    unten, oben, begrenzt = 0, 100, False
    for schritt in endpunkt.pfad:
        antwort = graph.antwort(schritt.knoten, schritt.antwort or "")
        if antwort and antwort.alter and not antwort.alter.unbekannt:
            begrenzt = True
            unten = max(unten, antwort.alter.min if antwort.alter.min is not None else 0)
            oben = min(oben, antwort.alter.max if antwort.alter.max is not None else 100)
    if not begrenzt:
        return ERWACHSEN
    if oben >= 100:
        oben = ERWACHSEN[1]
    return (unten, max(unten, oben))


SONDERSTUFEN = {
    "RD_Mehrere": 1,
    "RD_BT_NA": 2,
    "RD_BT_RTW": 3,
    "BRAND M.": 3,
    "TH M.": 3,
    "BRAND K.": 4,
    "TH K.": 4,
}


def stufe(kategorie: str) -> int:
    """Return how urgent a category is, from 1 (most) to 5 (least)."""
    rd = re.match(r"RD(\d)", kategorie)
    if rd:
        return int(rd.group(1))
    for anfang, wert in SONDERSTUFEN.items():
        if kategorie.startswith(anfang):
            return wert
    zahl = re.search(r"(\d+)", kategorie)
    if zahl:
        return 1 if int(zahl.group(1)) >= 6 else 2 if int(zahl.group(1)) >= 3 else 4
    return 5


STIMMUNGEN = {
    1: {"panisch": 45, "aufgeregt": 45, "verwirrt": 10},
    2: {"aufgeregt": 50, "panisch": 15, "ruhig": 25, "verwirrt": 10},
    3: {"aufgeregt": 40, "ruhig": 45, "verwirrt": 15},
    4: {"ruhig": 60, "aufgeregt": 25, "verwirrt": 15},
    5: {"ruhig": 70, "aufgeregt": 20, "verwirrt": 10},
}


@dataclass
class Person:
    """The affected person as the opening describes them, and what the code's path says of them."""

    alter: int
    weiblich: bool
    anrufer_selbst: bool
    stillstand: bool = False
    bewusstlos: bool = False
    atemnot: bool = False
    alter_bekannt: bool = True
    vor_ort: bool = True
    hand: str = BEIM_BETROFFENEN
    alter_geschaetzt: bool = False

    def alter_text(self) -> str:
        """Return the age as the caller says it: in years, or roughly, when only guessed."""
        return f"etwa {self.alter}" if self.alter_geschaetzt else str(self.alter)


STILLSTAND = re.compile(
    r"\btote?\b|leblos|atemstillstand|atmet nicht|keine atmung|nicht atmend|reanimation"
)
ATEMNOT = re.compile(r"ineffektiv|atemnot|schnappatmung|atmung (auffällig|erschwert)")
BEWUSSTLOS = re.compile(r"(?<!nicht )bewusstlos|reagiert nicht|nicht ansprechbar|krampf|nicht wach")
VOR_ORT = {
    SELBST: {VOR_ORT_JA: 1},
    BEIM_BETROFFENEN: {VOR_ORT_JA: 1},
    FUER_ANDERE: {"nein-nicht-mehr-vor-ort": 20, "nein-war-nicht-vor-ort": 75, "unbekannt": 5},
    GEHOERT: {"nein-war-nicht-vor-ort": 90, "unbekannt": 10},
    AUTOMATISCH: {"nein-war-nicht-vor-ort": 1},
}
HAND_RD = {SELBST: 25, BEIM_BETROFFENEN: 60, FUER_ANDERE: 10, GEHOERT: 5}
HAND_BRAND = {SELBST: 25, BEIM_BETROFFENEN: 35, FUER_ANDERE: 25, GEHOERT: 15}
HAND_TH = {SELBST: 25, BEIM_BETROFFENEN: 40, FUER_ANDERE: 25, GEHOERT: 10}
HAND_JE_PROTOKOLL = {
    "rd.33": {BEIM_BETROFFENEN: 70, FUER_ANDERE: 30},
    "rd.34": {AUTOMATISCH: 1},
    "rd.39": {SELBST: 30, BEIM_BETROFFENEN: 40, FUER_ANDERE: 10, GEHOERT: 20},
    "rd.24": {SELBST: 40, BEIM_BETROFFENEN: 60},
    "fw.brand.brandmeldeanlage": {BEIM_BETROFFENEN: 20, FUER_ANDERE: 30, AUTOMATISCH: 50},
    "fw.th.tueroeffnung": {SELBST: 10, BEIM_BETROFFENEN: 20, FUER_ANDERE: 60, GEHOERT: 10},
    "fw.th.aufzugnotbefreiung": {SELBST: 50, BEIM_BETROFFENEN: 40, FUER_ANDERE: 10},
}
KRANKHEITSPROTOKOLLE = frozenset(
    f"rd.{n:02d}" for n in (1, 5, 6, 10, 12, 13, 18, 19, 24, 25, 26, 28, 31, 33)
)
MIT_ADRESSE = frozenset({"rd.33", "rd.34"})
STRASSENLAGEN = frozenset({"rd.29", "rd.34", "fw.th.verkehrsunfall", "fw.brand.fahrzeugbrand"})
SCHAUPLAETZE = {
    "rd.33": {"einrichtung": 70, "wohnung": 30},
    "rd.39": {"oeffentlich": 1},
    "fw.brand.brandmeldeanlage": {"oeffentlich": 1},
    "fw.brand.industrie-und-gewerbebrand": {"betrieb": 1},
    "fw.brand.brand-im-freien": {"draussen": 1},
    "fw.brand.brand-in-verkehrsanlagen": {"oeffentlich": 1},
    "fw.brand.brand-in-sonderobjekt": {"einrichtung": 1},
    "fw.th.aufzugnotbefreiung": {"oeffentlich": 50, "wohnung": 50},
    "fw.th.tierrettung": {"draussen": 70, "gewaesser": 30},
    "fw.th.person-in-notlage": {"draussen": 50, "gewaesser": 20, "wohnung": 30},
    "fw.th.einsturz-gebaeudeschaden": {"betrieb": 50, "wohnung": 50},
}
RD_SCHAUPLAETZE = {"wohnung": 76, "strasse": 10, "draussen": 10, "betrieb": 2, "gewaesser": 2}
ERTRINKEN = "rd.14"
BADEWANNE_BIS = 5
IM_WASSER = re.compile(r"im wasser|ertrink|\beis\b")
BAUSTELLE = re.compile(r"baugrube|\bgraben\b|\bsilo\b|schacht|\bkran\b|baustelle|einsturz")
OEFFENTLICH_FUER = {
    "rd.39": frozenset({"Schule", "Einkaufszentrum", "Bahnhof", "Hochschule", "Universität"}),
    "fw.brand.brandmeldeanlage": frozenset(
        {"Hotel", "Kaufhaus", "Schule", "Klinik", "Einkaufszentrum", "Hochschule", "Museum"}
    ),
    "fw.brand.brand-in-verkehrsanlagen": frozenset({"Bahnhof", "Haltepunkt"}),
}
AM_WASSER = frozenset({"Gewässer", "Fluss", "Kanal", "Strand", "Ufer"})
SCHAUPLATZ_ARTEN = {
    "draussen": frozenset(
        {"Park", "Wald", "Friedhof", "Kleingartenanlage", "Spielplatz", "Sportplatz"}
    ),
    "gewaesser": AM_WASSER | {"Schwimmbad"},
}
EINRICHTUNGEN = (
    "Pflegeheim Haus Sonnenhof",
    "Seniorenresidenz Am Park",
    "Hausarztpraxis Dr. Berg",
    "Praxisgemeinschaft am Markt",
    "Tagespflege Lindenhof",
)
BETRIEBE = (
    "Tischlerei Krüger",
    "Baustelle Wohnanlage",
    "Lager der Spedition Nord",
    "Metallbau Schulze",
    "Großbäckerei am Hafen",
)
STRASSENSTELLEN = ("Fahrbahn vor dem Haus", "Kreuzung", "Gehweg vor dem Haus")
RAHMEN_JE_ART = {
    **dict.fromkeys(("Schule", "Kita", "Hochschule", "Universität"), "schule"),
    **dict.fromkeys(
        ("Bahnhof", "Haltepunkt", "Bushaltestelle", "Tramhaltestelle", "Busbahnhof"), "verkehr"
    ),
    **dict.fromkeys(
        ("Biergarten", "Theater", "Kino", "Kirche", "Moschee", "Museum", "Kulturzentrum"), "kultur"
    ),
    **dict.fromkeys(
        (
            "Park",
            "Wald",
            "Friedhof",
            "Kleingartenanlage",
            "Spielplatz",
            "Brunnen",
        ),
        "draussen",
    ),
    **dict.fromkeys(("Sportplatz", "Sportanlage", "Sporthalle"), "sport"),
    **dict.fromkeys(("Gewässer", "Fluss", "Kanal", "Ufer"), "gewaesser"),
    **dict.fromkeys(("Strand", "Schwimmbad"), "bad"),
    **dict.fromkeys(("Pflegeheim", "Klinik"), "einrichtung"),
}
SCHWANGER = re.compile(r"schwanger|geburt|wehen|fehlgeburt|trimester|ssw")
ALTERSSCHWER = frozenset({"rd.10", "rd.19", "rd.28"})


def stillstand_wahl(graph: Abfragegraph) -> str:
    """Return the node where cardiac arrest is first chosen: its protocol's shallowest choice."""
    wahlen = [
        id_
        for id_, knoten in graph.knoten.items()
        if any(antwort.protokoll == STILLSTAND_PROTOKOLL for antwort in knoten.antworten or [])
    ]
    return min(wahlen, key=lambda id_: graph.tiefen.get(id_, len(graph.knoten)), default="")


def nur_ueber_stillstand(graph: Abfragegraph) -> frozenset[tuple[str, str]]:
    """Return the endpoints that need an arrest but are not reached through its shortcut.

    Worked out once per graph, since it reads the path of every endpoint, and kept on the graph
    the way its own cached properties are.
    """
    gemerkt = graph.__dict__.get(UMWEGE_SCHLUESSEL)
    if gemerkt is None:
        wahl = stillstand_wahl(graph)
        gemerkt = frozenset(
            (e.protokoll, e.knoten)
            for e in graph.endpunkte
            if e.pfad and e.pfad[0].knoten != wahl and stillstand_von(graph, e)
        )
        graph.__dict__[UMWEGE_SCHLUESSEL] = gemerkt
    return gemerkt


def stillstand_von(graph: Abfragegraph, endpunkt: Endpunkt) -> bool:
    """Tell whether a code needs a person who does not breathe."""
    return (
        endpunkt.protokoll == STILLSTAND_PROTOKOLL
        or endpunkt.kategorie.startswith(("RD1NC REA", "RD1NC NNAD"))
        or bool(STILLSTAND.search(pfadtext(graph, endpunkt)))
    )


def zustand_gewichte(endpunkt: Endpunkt, person: Person) -> dict[str, dict[str, float]]:
    """Return how the person reacts and breathes, so the opening never contradicts the code.

    The protocol for dead persons, a resuscitation code or a path that speaks of arrest means no
    reaction and no breathing; a path that speaks of unconsciousness or a seizure means no normal
    reaction, one that speaks of laboured or ineffective breathing means breathing that stands
    out; the least urgent codes mean awake and breathing normally. A caller who is the
    affected person is awake.
    """
    if person.stillstand:
        return {"rd.reaktion": {"reagiert-nicht": 1}, "rd.atmung": {"atmet-nicht": 1}}
    gewichte = zustand_ohne_atemnot(endpunkt, person)
    if person.atemnot:
        gewichte["rd.atmung"] = {"atmung-auffaellig": 1}
    if endpunkt.kategorie.startswith(("RD4", "RD5")):
        return gewichte
    unbekannt = {FUER_ANDERE: 0.3, GEHOERT: 0.7}.get(person.hand)
    if unbekannt is None:
        return gewichte
    return {knoten: unsicher(werte, unbekannt) for knoten, werte in gewichte.items()}


def unsicher(gewichte: dict[str, float], anteil: float) -> dict[str, float]:
    """Return weights where "unbekannt" makes up the given share, as for a caller not on site."""
    rest = {a: g for a, g in gewichte.items() if a != "unbekannt"}
    summe = sum(rest.values()) or 1
    return {**{a: g / summe * (1 - anteil) for a, g in rest.items()}, "unbekannt": anteil}


def zustand_ohne_atemnot(endpunkt: Endpunkt, person: Person) -> dict[str, dict[str, float]]:
    """Return reaction and breathing for a person who is not in arrest."""
    if person.bewusstlos:
        return {
            "rd.reaktion": {"reagiert-nicht": 60, "reagiert-aber-nicht-normal": 40},
            "rd.atmung": {"atmung-auffaellig": 60, "ja-normale-atmung": 30, "unbekannt": 10},
        }
    if endpunkt.kategorie.startswith(("RD4", "RD5")):
        return {"rd.reaktion": {WACH: 1}, "rd.atmung": {"ja-normale-atmung": 1}}
    reaktion = (
        {WACH: 1}
        if person.anrufer_selbst
        else {WACH: 60, "reagiert-aber-nicht-normal": 30, "unbekannt": 10}
    )
    return {
        "rd.reaktion": reaktion,
        "rd.atmung": (
            {"ja-normale-atmung": 60, "atmung-auffaellig": 35}
            if person.anrufer_selbst
            else {"ja-normale-atmung": 60, "atmung-auffaellig": 35, "unbekannt": 5}
        ),
    }


def regeln(endpunkt: Endpunkt, person: Person) -> dict[str, dict[str, float]]:
    """Return the weights of the opening answers that fit the code, by node.

    A node not named here, or an answer not weighted, is chosen with equal chance among the rest.
    Who reports is drawn before (`hand_ziehen`); whether they are on site follows from that, see
    `VOR_ORT`.
    """
    return {
        "eroeffnung.hand": {person.hand: 1},
        "rd.anzahl": anzahl_gewichte(endpunkt),
        "rd.geschlecht": {"frau": 1} if person.weiblich else {"mann": 1},
        **zustand_gewichte(endpunkt, person),
    }


def hergang(endpunkt: Endpunkt, person: Person, schauplatz: str, zufall: random.Random) -> str:
    """Return how the arrest came about, for the trainer to tell: fitting the age and the place.

    A person found clearly dead has no story beyond being found; for them nothing is told here.
    A newborn has its own stories, since the age alone does not tell a newborn from an infant.
    """
    if endpunkt.code.startswith(TODESZEICHEN):
        return ""
    if endpunkt.knoten == NEUGEBORENES:
        return zufall.choice(NEUGEBORENEN_HERGAENGE)
    passende = [
        text
        for text, unten, oben, ort in HERGAENGE
        if unten <= person.alter <= oben and ort in (None, schauplatz, OBERRAHMEN.get(schauplatz))
    ]
    return zufall.choice(passende) if passende else ""


def mit_hand(person: Person, endpunkt: Endpunkt, text: str, zufall: random.Random) -> Person:
    """Draw who reports and mark whether that is the affected person."""
    person.hand = hand_ziehen(endpunkt, person, text, zufall)
    person.anrufer_selbst = person.hand == SELBST
    return person


def hand_ziehen(endpunkt: Endpunkt, person: Person, text: str, zufall: random.Random) -> str:
    """Draw who reports, so that it fits the code.

    A cardiac arrest is reported by someone with the person, who can be guided through CPR. A
    path that names the caller, or says nobody has looked, decides it. Some protocols have their
    own callers (`HAND_JE_PROTOKOLL`). Nobody reports themselves when unconscious, trapped, in the
    water, under 14, or in a first-priority medical case; the least urgent codes are not reported
    by someone who only heard of them.
    """
    if person.stillstand:
        return BEIM_BETROFFENEN
    if NENNT_SELBST.search(text) and (endpunkt.fachrichtung != "rd" or person.alter >= 14):
        return SELBST
    standard = {"rd": HAND_RD, "brand": HAND_BRAND}.get(endpunkt.fachrichtung, HAND_TH)
    gewichte = dict(HAND_JE_PROTOKOLL.get(endpunkt.protokoll, standard))
    if NIEMAND_DA.search(text):
        gewichte = {h: g for h, g in gewichte.items() if h in (FUER_ANDERE, AUTOMATISCH)}
        gewichte = gewichte or {FUER_ANDERE: 1}
    if BESTAETIGT.search(text) or NENNT_SELBST_ODER_DABEI.search(text):
        gewichte = {h: g for h, g in gewichte.items() if h in (SELBST, BEIM_BETROFFENEN)}
    medizinisch = endpunkt.fachrichtung == "rd"
    if OHNE_SELBST.search(text) or (
        medizinisch
        and (person.bewusstlos or person.alter < 14 or endpunkt.kategorie.startswith("RD1"))
    ):
        gewichte.pop(SELBST, None)
    if endpunkt.kategorie.startswith(("RD4", "RD5")):
        gewichte.pop(GEHOERT, None)
    if not gewichte:
        return BEIM_BETROFFENEN
    return zufall.choices(list(gewichte), weights=list(gewichte.values()))[0]


def anzahl_gewichte(endpunkt: Endpunkt) -> dict[str, float]:
    """Return how many people the code speaks of, read from its category and reason.

    Illnesses strike one person; gas and smoke often more than one.
    """
    if endpunkt.kategorie.startswith("RD_Mehrere"):
        return {"drei-oder-mehr": 1}
    treffer = re.search(r"(mehr als )?(\d+) (Patienten|Personen|Verletzte)", endpunkt.anlass)
    if treffer:
        zahl = int(treffer.group(2)) + (1 if treffer.group(1) else 0)
        return {"zwei-personen": 1} if zahl == 2 else {"drei-oder-mehr": 1}
    if re.search(
        r"mehrere[nm]? (Verletz|Patienten|Betroffene|eingeklemmt|Personen)", endpunkt.anlass, re.I
    ):
        return {"zwei-personen": 1, "drei-oder-mehr": 2}
    if endpunkt.protokoll in KRANKHEITSPROTOKOLLE:
        return {"eine-person": 1}
    if endpunkt.protokoll == "rd.08":
        return {"eine-person": 60, "zwei-personen": 30, "drei-oder-mehr": 10}
    return {"eine-person": 93, "zwei-personen": 7}


def waehlen(knoten: Knoten, gewichte: dict[str, float], zufall: random.Random) -> str:
    """Choose an answer of a node by the weights given, else among all with equal chance."""
    antworten = knoten.antworten or []
    passend = [a for a in antworten if gewichte.get(a.id, 0) > 0]
    if passend:
        return zufall.choices(passend, weights=[gewichte[a.id] for a in passend])[0].id
    return zufall.choice(antworten).id


def eroeffnung(
    graph: Abfragegraph, endpunkt: Endpunkt, person: Person, zufall: random.Random
) -> dict[str, Wahl]:
    """Answer the questions from the root to the code's protocol choice, fitting the code."""
    wahl = endpunkt.pfad[0].knoten
    tabelle = regeln(endpunkt, person)
    antworten: dict[str, Wahl] = {}
    id_ = graph.meta.wurzel
    for _ in range(100):
        if id_ == wahl:
            return antworten
        knoten = graph.knoten[id_]
        if knoten.weiche is not None:
            vorher = antworten[knoten.weiche.knoten].antwort or ""
            id_ = knoten.weiche.ziele[vorher]
        elif knoten.eingabe is not None:
            antworten[id_] = Wahl(wert=person.alter_text()) if person.alter_bekannt else Wahl()
            id_ = knoten.ziel or ""
        else:
            if id_ == graph.meta.wurzel:
                gewichte = {endpunkt.fachrichtung: 1}
            elif id_ == "eroeffnung.vor-ort":
                gewichte = VOR_ORT.get(antworten["eroeffnung.hand"].antwort or "", {})
            else:
                gewichte = tabelle.get(id_, {})
            gewaehlt = waehlen(knoten, gewichte, zufall)
            antwort = graph.antwort(id_, gewaehlt)
            antworten[id_] = Wahl(antwort=gewaehlt, label=antwort.label if antwort else None)
            id_ = antwort.ziel if antwort else ""
    raise NichtsZuZiehen(f"Die Eröffnung führt nicht zur Wahl {wahl}.")


def schauplatz_ziehen(
    endpunkt: Endpunkt, text: str, alter: int, erzeugung: Erzeugung, zufall: random.Random
) -> str:
    """Draw the kind of scene the situation plays at.

    A traffic accident is on the street, a drowning at the water (a small child also in the
    bathtub), a care home's request in the home; homes are where the flat protocols play. Medical
    calls otherwise happen at a named place in the share the settings give, else mostly at home
    and now and then on the street, outdoors, at work or by the water.
    """
    if endpunkt.code in ("09B01b", "09B01f") or endpunkt.protokoll in STRASSENLAGEN:
        return "strasse"
    if endpunkt.protokoll == ERTRINKEN:
        return "wohnung" if alter <= BADEWANNE_BIS and zufall.random() < 0.15 else "gewaesser"
    if IM_WASSER.search(text) and endpunkt.fachrichtung == "rd":
        return "gewaesser"
    if endpunkt.protokoll in SCHAUPLAETZE:
        return gewichtet(SCHAUPLAETZE[endpunkt.protokoll], zufall)
    if endpunkt.protokoll == "rd.22" or (endpunkt.fachrichtung == "rd" and BAUSTELLE.search(text)):
        return gewichtet({"betrieb": 70, "draussen": 30}, zufall)
    if endpunkt.protokoll == "rd.15":
        return "draussen" if "blitz" in text else gewichtet({"wohnung": 60, "betrieb": 40}, zufall)
    if endpunkt.protokoll in WOHNUNGSPROTOKOLLE or endpunkt.code.startswith(TODESZEICHEN):
        return "wohnung"
    if endpunkt.fachrichtung != "rd":
        return "draussen" if "freien" in text else "wohnung"
    if zufall.random() * 100 < erzeugung.anteil_orte:
        return "oeffentlich"
    return gewichtet(RD_SCHAUPLAETZE, zufall)


def gewichtet(gewichte: dict[str, float], zufall: random.Random) -> str:
    """Draw one key of a weight table."""
    return zufall.choices(list(gewichte), weights=list(gewichte.values()))[0]


@dataclass
class Schauplatz:
    """Where the scenario plays: the place, its Ortsteil, the kind of scene and its frame.

    The frame narrows the scene for who calls and what happened: a park is outdoors, a pool is
    water, a school has teachers.
    """

    ort: Ort
    ortsteil: str
    art: str
    rahmen: str


def ort_ziehen(
    quellen: Quellen,
    erzeugung: Erzeugung,
    zufall: random.Random,
    art: str = "wohnung",
    protokoll: str = "",
) -> Schauplatz:
    """Return the place for a kind of scene.

    Public places, outdoor places and the water are named places with the nearest door's address,
    within a Bezirk setting when one is made; homes are a random door; the street is a door with
    the spot named; homes for the elderly, practices and workplaces are a door with a made-up
    name. When no fitting named place turns up, the street in front of a random door stands in,
    and without the address list a random named place.
    """
    if art in SCHAUPLATZ_ARTEN or art == "oeffentlich":
        arten = OEFFENTLICH_FUER.get(protokoll) or SCHAUPLATZ_ARTEN.get(art, EINSATZORTE)
        am_platz = platz_mit_adresse(quellen, erzeugung, zufall, arten)
        if am_platz is not None:
            ort, ortsteil, platzart = am_platz
            rahmen = RAHMEN_JE_ART.get(platzart, art)
            return Schauplatz(ort, ortsteil, art, rahmen)
        art = "strasse"
    adresse = quellen.adresse(zufall, erzeugung.ortsteil, erzeugung.bezirk)
    if adresse is not None:
        ort = ort_aus(adresse)
        rahmen = art
        if art == "strasse":
            ort.objekt = zufall.choice(STRASSENSTELLEN)
            rahmen = "verkehr"
        elif art == "einrichtung":
            ort.objekt = zufall.choice(EINRICHTUNGEN)
        elif art == "betrieb":
            ort.objekt = zufall.choice(BETRIEBE)
        return Schauplatz(ort, adresse["ortsteil"], art, rahmen)
    platz = quellen.ort(zufall, erzeugung.ortsteil)
    if platz is None and (erzeugung.ortsteil or erzeugung.bezirk):
        raise NichtsZuZiehen("Im gewählten Gebiet gibt es keine Adresse und keinen Ort.")
    if platz is None:
        raise NichtsZuZiehen("Weder das Adressverzeichnis noch die Orte sind geladen.")
    ort = Ort(
        adresse=Adresse(ortsteil=platz["ortsteil"]),
        koordinaten=(platz["breite"], platz["laenge"]),
        objekt=platz["name"],
    )
    rahmen = RAHMEN_JE_ART.get(platz.get("art", ""), "oeffentlich")
    return Schauplatz(ort, platz["ortsteil"], "oeffentlich", rahmen)


def platz_mit_adresse(
    quellen: Quellen,
    erzeugung: Erzeugung,
    zufall: random.Random,
    arten: frozenset[str] = EINSATZORTE,
) -> tuple[Ort, str, str] | None:
    """Return a named place of the given kinds with the nearest door's address, and its kind."""
    for _ in range(PLATZ_VERSUCHE):
        platz = quellen.ort(zufall, erzeugung.ortsteil, arten)
        if platz is None:
            return None
        tuer = quellen.naechste(platz["breite"], platz["laenge"])
        if tuer is None or (erzeugung.bezirk and tuer["bezirk"] != erzeugung.bezirk):
            continue
        ort = ort_aus(tuer)
        ort.koordinaten = (platz["breite"], platz["laenge"])
        ort.objekt = f"{platz['name']} ({platz['art']})"
        return ort, tuer["ortsteil"], platz.get("art", "")
    return None


def ort_aus(adresse: dict) -> Ort:
    """Return a scenario location at a door of the address list."""
    return Ort(
        adresse=Adresse(
            strasse=adresse["strasse"],
            hausnummer=adresse["hausnummer"],
            plz=adresse["plz"],
            ortsteil=adresse["ortsteil"],
        ),
        koordinaten=(adresse["breite"], adresse["laenge"]),
    )


def anrufer_ziehen(zufall: random.Random, name: str) -> Anrufer:
    """Return a caller with a shown number, or a withheld one, and sometimes another callback."""
    nummer = mobilnummer(zufall) if zufall.random() < 0.6 else festnetznummer(zufall)
    los = zufall.random()
    if los < UNTERDRUECKT_ANTEIL:
        return Anrufer(name=name, rufnummer_unterdrueckt=True, rueckrufnummer=nummer)
    if los < UNTERDRUECKT_ANTEIL + ANDERE_RUECKRUF_ANTEIL:
        return Anrufer(name=name, rufnummer=nummer, rueckrufnummer=mobilnummer(zufall))
    return Anrufer(name=name, rufnummer=nummer)


def draussen_ziehen(
    quellen: Quellen, erzeugung: Erzeugung, arten: tuple[str, ...], zufall: random.Random
) -> Schauplatz | None:
    """Return a place outside for a caller who does not know the address, if one turns up.

    People in a building usually know its address; outside, in a park or by the water, they
    often do not. The kind of place fits the situation and the scene. The point lies a
    little off the place's centre, close enough that choosing the place counts as the right point,
    the caller names the place only half the time, and describes two or three other named places
    nearby by direction and distance. A place with fewer than two such neighbours is not taken.
    """
    for _ in range(PLATZ_VERSUCHE):
        platz = quellen.ort(zufall, erzeugung.ortsteil, arten)
        if platz is None:
            return None
        richtung = zufall.uniform(0, 2 * math.pi)
        abstand = zufall.uniform(*DRAUSSEN_VERSATZ)
        hier = (
            platz["breite"] + abstand * math.cos(richtung) / METER_JE_GRAD,
            platz["laenge"]
            + abstand
            * math.sin(richtung)
            / (METER_JE_GRAD * math.cos(math.radians(platz["breite"]))),
        )
        nahe = list(
            {
                o["name"]: o
                for o in reversed(quellen.umkreis(*hier, UMGEBUNG_RADIUS))
                if o["name"] != platz["name"]
            }.values()
        )
        nahe.sort(key=lambda o: entfernung(hier, (o["breite"], o["laenge"])))
        if len(nahe) < 2:
            continue
        gesehen = zufall.sample(nahe[:8], min(len(nahe[:8]), zufall.randint(2, 3)))
        umgebung = sorted((umgebungsort(hier, o) for o in gesehen), key=lambda o: o.meter)
        art = platz.get("art", "")
        wo = platz["name"] if zufall.random() < 0.5 else DRAUSSEN_ARTEN.get(art, "draußen")
        ort = Ort(
            adresse=Adresse(ortsteil=platz["ortsteil"]),
            koordinaten=hier,
            objekt=platz["name"],
            ohne_adresse=OhneAdresse(wo=wo, umgebung=umgebung),
        )
        rahmen = RAHMEN_JE_ART.get(art, "draussen")
        return Schauplatz(ort, platz["ortsteil"], OBERRAHMEN.get(rahmen, rahmen), rahmen)
    return None


def umgebungsort(hier: tuple[float, float], anderer: dict) -> Umgebungsort:
    """Describe a nearby place as the caller sees it: direction, and distance to 50 metres."""
    dort = (anderer["breite"], anderer["laenge"])
    return Umgebungsort(
        name=anderer["name"],
        art=anderer["art"],
        richtung=himmelsrichtung(hier, dort),
        meter=max(50, round(entfernung(hier, dort) / 50) * 50),
    )


def himmelsrichtung(von: tuple[float, float], nach: tuple[float, float]) -> str:
    """Return the compass direction from one point to another, in eight steps."""
    dy = nach[0] - von[0]
    dx = (nach[1] - von[1]) * math.cos(math.radians(von[0]))
    winkel = (math.degrees(math.atan2(dx, dy)) + 360) % 360
    return HIMMELSRICHTUNGEN[round(winkel / 45) % 8]


def mit_funkzelle(
    anrufer: Anrufer,
    ort: Ort,
    zufall: random.Random,
    vor_ort: str = VOR_ORT_JA,
    quellen: Quellen | None = None,
) -> Anrufer:
    """Give a caller on a shown mobile number the cell their call comes through.

    The cell is made up, not a real mast: its radius lies in `FUNKZELLE_RADIUS`. It lies around
    the caller: for a caller on site off the true point by a fraction of the radius, so the point
    is always inside; for one who has left, up to two kilometres away; for one who was never there,
    around another door of the city, so the trainee cannot trust it for the place. When it is not
    known where the caller is, there is no cell.
    """
    if not anrufer.mobil_angezeigt() or ort.koordinaten is None or vor_ort == "unbekannt":
        return anrufer
    radius = zufall.uniform(*FUNKZELLE_RADIUS)
    abstand = zufall.uniform(FUNKZELLE_VERSATZ[0], min(FUNKZELLE_VERSATZ[1], radius * 0.8))
    breite, laenge = ort.koordinaten
    if vor_ort == "nein-nicht-mehr-vor-ort":
        abstand = zufall.uniform(radius, 2000)
    elif vor_ort != VOR_ORT_JA:
        anderswo = quellen.adresse(zufall, "", "") if quellen else None
        if anderswo is None:
            return anrufer
        breite, laenge = anderswo["breite"], anderswo["laenge"]
    richtung = zufall.uniform(0, 2 * math.pi)
    mitte = (
        breite + abstand * math.cos(richtung) / METER_JE_GRAD,
        laenge + abstand * math.sin(richtung) / (METER_JE_GRAD * math.cos(math.radians(breite))),
    )
    return anrufer.model_copy(update={"funkzelle": Funkzelle(mitte=mitte, radius=round(radius))})


def person_ziehen(graph: Abfragegraph, endpunkt: Endpunkt, zufall: random.Random) -> Person:
    """Return the affected person: an age the code allows, a sex, and whether they call."""
    unten, oben = TODESZEICHEN_ALTER.get(endpunkt.code, altersspanne(graph, endpunkt))
    if endpunkt.code in LIEGEZEIT and zufall.random() < 0.7:
        unten = 65
    text = pfadtext(graph, endpunkt)
    if SCHWANGER.search(text):
        unten, oben = max(unten, 16), max(max(unten, 16), min(oben, 45))
    if endpunkt.protokoll in ALTERSSCHWER and oben >= 45 and unten < 45:
        unten, oben = (45, oben) if zufall.random() < 0.8 else (unten, 44)
    alter = zufall.randint(unten, oben)
    vorgegeben = {
        antwort.geschlecht
        for schritt in endpunkt.pfad
        if (antwort := graph.antwort(schritt.knoten, schritt.antwort or "")) and antwort.geschlecht
    }
    if vorgegeben == {"m"}:
        weiblich = False
    else:
        weiblich = "w" in vorgegeben or bool(re.search(r"schwanger|geburt", text))
        weiblich = weiblich or zufall.random() < 0.5
    stillstand = stillstand_von(graph, endpunkt)
    bewusstlos = stillstand or bool(BEWUSSTLOS.search(text))
    atemnot = bool(ATEMNOT.search(text))
    alter_bekannt = not any(
        (antwort := graph.antwort(s.knoten, s.antwort or ""))
        and antwort.alter
        and antwort.alter.unbekannt
        for s in endpunkt.pfad
    )
    person = Person(alter, weiblich, False, stillstand, bewusstlos, atemnot, alter_bekannt)
    mit_hand(person, endpunkt, text, zufall)
    if person.hand == GEHOERT:
        begrenzt = altersspanne(graph, endpunkt) != ERWACHSEN
        person.alter_bekannt = person.alter_bekannt and begrenzt
        if begrenzt:
            person.alter, person.alter_geschaetzt = geschaetztes_alter(alter, unten, oben), True
    return person


def geschaetztes_alter(alter: int, unten: int, oben: int) -> int:
    """Return an age as someone guesses it from afar: to 10 years, children to 2, at least 1.

    The guess stays within the ages the code allows.
    """
    schritt = 2 if alter <= 12 else 10
    geschaetzt = max(1, round(alter / schritt) * schritt)
    return min(max(geschaetzt, max(unten, 1)), max(oben, 1))


def titel_von(graph: Abfragegraph, endpunkt: Endpunkt) -> str:
    """Return a scenario's name: the code's reason, or its protocol when the reason is the code."""
    if endpunkt.anlass and endpunkt.anlass != endpunkt.code:
        return endpunkt.anlass
    wahl = endpunkt.pfad[0]
    protokoll = graph.antwort(wahl.knoten, wahl.antwort or "")
    return f"{protokoll.label} ({endpunkt.code})" if protokoll else endpunkt.code


def gleichwertige(
    graph: Abfragegraph, knoten_id: str, antwort_id: str, person: Person, zufall: random.Random
) -> Antwort | None:
    """Return the answer at a node, or by chance another one when the node does not decide the way.

    Some questions do not change the code but what the caller is told, such as whether the way
    out of a burning building is clear: all their answers lead on to the same question. Drawing
    among them varies the scenarios. A caller who is not on site is not in the building either.
    """
    gewaehlt = graph.antwort(knoten_id, antwort_id)
    antworten = graph.knoten[knoten_id].antworten or []
    if gewaehlt is None or len({antwort.ziel for antwort in antworten}) != 1:
        return gewaehlt
    if knoten_id in NICHT_VOR_ORT_ANTWORT and not person.vor_ort:
        return graph.antwort(knoten_id, NICHT_VOR_ORT_ANTWORT[knoten_id])
    return zufall.choice(antworten)


def warntafel_ziehen(quellen: Quellen, person: Person, zufall: random.Random) -> Wahl:
    """Draw the plate the caller reads out.

    Only a caller on site can read one, and even then smoke or distance sometimes keep them from
    it (`TAFEL_UNLESBAR`); without a list of goods there is none to read.
    """
    if not quellen.gefahrstoffe or not person.vor_ort or zufall.random() < TAFEL_UNLESBAR:
        return Wahl()
    return Wahl(wert=tafel(zufall.choice(quellen.gefahrstoffe)))


def generieren(
    graph: Abfragegraph, quellen: Quellen, erzeugung: Erzeugung, zufall: random.Random
) -> Szenario:
    """Make up one complete scenario that fits the settings.

    The situation comes first, then who is affected and how the call opens, then the place, and
    only then who calls and what happened, so these fit the place the scenario really plays at.
    """
    endpunkt = endpunkt_ziehen(graph, erzeugung, zufall)
    text = pfadtext(graph, endpunkt)
    rd = endpunkt.fachrichtung == "rd"
    if rd:
        person = person_ziehen(graph, endpunkt, zufall)
    else:
        person = mit_hand(Person(0, False, False), endpunkt, text, zufall)
    antworten = eroeffnung(graph, endpunkt, person, zufall)
    vor_ort = antworten.get("eroeffnung.vor-ort")
    person.vor_ort = vor_ort is None or vor_ort.antwort == VOR_ORT_JA
    for schritt in endpunkt.pfad:
        eingabe = graph.knoten[schritt.knoten].eingabe
        if eingabe is not None and eingabe.art == "warntafel":
            antworten[schritt.knoten] = warntafel_ziehen(quellen, person, zufall)
            continue
        antwort = gleichwertige(graph, schritt.knoten, schritt.antwort or "", person, zufall)
        antworten[schritt.knoten] = Wahl(
            antwort=antwort.id if antwort else schritt.antwort,
            label=antwort.label if antwort else None,
        )
    betroffen = zufallsname(zufall, person.weiblich) if rd else ""
    anrufer_weiblich = person.weiblich if person.anrufer_selbst and rd else zufall.random() < 0.5
    anrufer_name = (
        betroffen if person.anrufer_selbst and betroffen else zufallsname(zufall, anrufer_weiblich)
    )
    anrufer = anrufer_ziehen(zufall, anrufer_name)
    art = schauplatz_ziehen(endpunkt, text, person.alter, erzeugung, zufall)
    schauplatz = None
    if (
        anrufer.mobil_angezeigt()
        and person.vor_ort
        and endpunkt.protokoll not in MIT_ADRESSE
        and (rd or endpunkt.protokoll in DRAUSSEN_PROTOKOLLE)
        and (art in ("draussen", "gewaesser") or endpunkt.protokoll == "fw.th.verkehrsunfall")
        and not erzeugung.bezirk
        and zufall.random() * 100 < erzeugung.anteil_ohne_adresse
    ):
        schauplatz = draussen_ziehen(quellen, erzeugung, draussen_arten(endpunkt, art), zufall)
    if schauplatz is None:
        schauplatz = ort_ziehen(quellen, erzeugung, zufall, art, endpunkt.protokoll)
    ort = schauplatz.ort
    rahmen = rahmen_fuer(endpunkt, schauplatz)
    beziehung = beziehung_ziehen(
        person.hand,
        rahmen,
        person.alter if rd else None,
        endpunkt.fachrichtung,
        endpunkt.protokoll,
        anrufer_weiblich,
        zufall,
    )
    anrufer = anrufer.model_copy(update={"beziehung": beziehung.text})
    kennt_wohnung = person.anrufer_selbst or beziehung.vertraut or person.hand == BEIM_BETROFFENEN
    if (
        schauplatz.art == "wohnung"
        and (rd or endpunkt.protokoll in WOHNUNGSPROTOKOLLE)
        and ort.adresse.hausnummer
        and not ort.objekt
        and kennt_wohnung
    ):
        ort.geschoss = geschoss_fuer(endpunkt, zufall)
        ort.klingel = (betroffen or anrufer_name).split()[-1]
        if (person.anrufer_selbst or beziehung.vertraut) and zufall.random() < HAUSTIER_ANTEIL:
            ort.haustier = zufall.choice(HAUSTIERE)
    stimmungen = STIMMUNGEN[stufe(endpunkt.kategorie)]
    stimmung = zufall.choices(list(stimmungen), weights=list(stimmungen.values()))[0]
    if stimmung == "panisch" and person.hand in (GEHOERT, AUTOMATISCH):
        stimmung = "aufgeregt"
    notizen = " ".join(
        teil
        for teil in (
            beziehung.notiz,
            hergang(endpunkt, person, rahmen, zufall) if person.stillstand else "",
        )
        if teil
    )
    ortsteil = schauplatz.ortsteil
    return Szenario(
        abfrage_version=graph.meta.version,
        titel=f"{titel_von(graph, endpunkt)}, {ortsteil}",
        herkunft=Herkunft.GENERIERT,
        ort=ort,
        anrufer=mit_funkzelle(
            anrufer,
            ort,
            zufall,
            vor_ort.antwort if vor_ort is not None and vor_ort.antwort else VOR_ORT_JA,
            quellen,
        ),
        betroffener=Betroffener(name=betroffen) if rd else None,
        antworten=antworten,
        ziel=Ziel(knoten=endpunkt.knoten, code=endpunkt.code),
        rolle=Rolle(stimmung=stimmung, notizen=notizen),
    )


def draussen_arten(endpunkt: Endpunkt, art: str) -> tuple[str, ...]:
    """Return the kinds of outdoor place a caller without an address may stand at."""
    if endpunkt.protokoll in DRAUSSEN_ARTEN_FUER:
        return DRAUSSEN_ARTEN_FUER[endpunkt.protokoll]
    if art == "gewaesser":
        return tuple(sorted(AM_WASSER))
    return DRAUSSEN_ARTEN_FUER["rd"]


def rahmen_fuer(endpunkt: Endpunkt, schauplatz: Schauplatz) -> str:
    """Return the frame a relationship and a back story are drawn for.

    A birth at home has the woman's people around her, a newborn's arrest the baby's parents.
    """
    if schauplatz.art != "wohnung":
        return schauplatz.rahmen
    if endpunkt.knoten == NEUGEBORENES:
        return "neugeborenes"
    if endpunkt.protokoll == "rd.24":
        return "geburt"
    return schauplatz.rahmen


def geschoss_fuer(endpunkt: Endpunkt, zufall: random.Random) -> str:
    """Return the floor of a home; a lift stuck at home is stuck between two floors."""
    if endpunkt.protokoll == "fw.th.aufzugnotbefreiung":
        unten = zufall.randint(1, 6)
        return f"zwischen {unten}. und {unten + 1}. OG"
    return zufall.choice(GESCHOSSE)
