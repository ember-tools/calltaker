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

import random
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from abfrage import Abfragegraph, Endpunkt, Knoten
from generator import festnetznummer, mobilnummer, zufallsname
from szenario import (
    Adresse,
    Anrufer,
    Betroffener,
    Herkunft,
    Ort,
    Rolle,
    Szenario,
    Wahl,
    Ziel,
)

NICHT_ZIEHBAR = {"", "Aufwertung entfällt."}
UNTERDRUECKT_ANTEIL = 0.05
ANDERE_RUECKRUF_ANTEIL = 0.05
ERWACHSEN = (18, 90)
PLATZ_VERSUCHE = 5
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

SELBST = "1-hand-der-anrufer-ist-selbst-betroffen"
BEIM_BETROFFENEN = "2-hand-der-anrufer-ist-beim-betroffenen"
FUER_ANDERE = "3-hand-der-anrufer-meldet-fuer-andere"
GEHOERT = "4-hand-der-anrufer-hat-es-nur-gehoert"

Disziplin = Literal["rd", "brand", "th"]


class Erzeugung(BaseModel):
    """What the trainer sets for made-up scenarios: weights, a category filter and an area."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    gewicht_rd: int = Field(80, ge=0, le=100)
    gewicht_brand: int = Field(12, ge=0, le=100)
    gewicht_th: int = Field(8, ge=0, le=100)
    kategorie: str = Field("", max_length=40)
    ortsteil: str = Field("", max_length=80)
    bezirk: str = Field("", max_length=80)
    anteil_orte: int = Field(30, ge=0, le=100)

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
    """Return the endpoints that may be drawn, by discipline and protocol."""
    filter_ = erzeugung.kategorie.strip().lower()
    nach: dict[Disziplin, dict[str, list[Endpunkt]]] = {}
    for endpunkt in graph.endpunkte:
        if endpunkt.kategorie in NICHT_ZIEHBAR or not endpunkt.pfad:
            continue
        if filter_ and not endpunkt.kategorie.lower().startswith(filter_):
            continue
        nach.setdefault(disziplin_von(endpunkt), {}).setdefault(endpunkt.protokoll, []).append(
            endpunkt
        )
    return nach


def endpunkt_ziehen(graph: Abfragegraph, erzeugung: Erzeugung, zufall: random.Random) -> Endpunkt:
    """Draw a discipline by weight, then a protocol and a code of it with equal chance."""
    nach = ziehbare(graph, erzeugung)
    gewichte = {d: g for d, g in erzeugung.gewichte().items() if g > 0 and d in nach}
    if not gewichte:
        raise NichtsZuZiehen("Kein Code passt zu diesen Einstellungen.")
    disziplin = zufall.choices(list(gewichte), weights=list(gewichte.values()))[0]
    protokoll = zufall.choice(sorted(nach[disziplin]))
    return zufall.choice(nach[disziplin][protokoll])


def altersspanne(graph: Abfragegraph, endpunkt: Endpunkt) -> tuple[int, int]:
    """Return the ages the answers on the code's path allow, adults when they say nothing."""
    unten, oben, begrenzt = 0, 100, False
    for schritt in endpunkt.pfad:
        antwort = graph.antwort(schritt.knoten, schritt.antwort or "")
        if antwort and antwort.alter:
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


STILLSTAND = re.compile(
    r"\btote?\b|leblos|atemstillstand|atmet nicht|keine atmung|nicht atmend|reanimation"
)
ATEMNOT = re.compile(r"ineffektiv|atemnot|schnappatmung|atmung (auffällig|erschwert)")
BEWUSSTLOS = re.compile(r"(?<!nicht )bewusstlos|reagiert nicht|nicht ansprechbar|krampf|nicht wach")
WACH = "ja-wach-und-ansprechbar"
VOR_ORT = {
    SELBST: {"ja-der-anrufer-ist-vor-ort": 1},
    BEIM_BETROFFENEN: {"ja-der-anrufer-ist-vor-ort": 1},
    FUER_ANDERE: {"ja-der-anrufer-ist-vor-ort": 60, "nein-war-nicht-vor-ort": 40},
    GEHOERT: {"nein-war-nicht-vor-ort": 70, "unbekannt": 30},
}


def pfadtext(graph: Abfragegraph, endpunkt: Endpunkt) -> str:
    """Return the reason and the answer labels after the protocol choice, lower-cased, to read it.

    The protocol's own name is left out: "Bewusstlosigkeit / Ohnmacht" names the topic, not the
    person's state.
    """
    labels = [
        antwort.label
        for schritt in endpunkt.pfad[1:]
        if (antwort := graph.antwort(schritt.knoten, schritt.antwort or "")) is not None
    ]
    return " ".join([endpunkt.anlass, *labels]).lower()


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
    return gewichte


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
        "rd.atmung": {"ja-normale-atmung": 60, "atmung-auffaellig": 35, "unbekannt": 5},
    }


def regeln(endpunkt: Endpunkt, person: Person) -> dict[str, dict[str, float]]:
    """Return the weights of the opening answers that fit the code, by node.

    A node not named here, or an answer not weighted, is chosen with equal chance among the rest.
    Whether the caller is on site follows from who reports, see `VOR_ORT`.
    """
    if endpunkt.fachrichtung != "rd":
        hand = {SELBST: 40, FUER_ANDERE: 50, GEHOERT: 10}
    elif person.anrufer_selbst:
        hand = {SELBST: 1}
    else:
        hand = {BEIM_BETROFFENEN: 75, FUER_ANDERE: 20, GEHOERT: 5}
    return {
        "eroeffnung.hand": hand,
        "rd.anzahl": anzahl_gewichte(endpunkt),
        "rd.geschlecht": {"frau": 1} if person.weiblich else {"mann": 1},
        **zustand_gewichte(endpunkt, person),
    }


def anzahl_gewichte(endpunkt: Endpunkt) -> dict[str, float]:
    """Return how many people the code speaks of, read from its category and reason."""
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
            antworten[id_] = Wahl(wert=str(person.alter))
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


def ort_ziehen(quellen: Quellen, erzeugung: Erzeugung, zufall: random.Random) -> tuple[Ort, str]:
    """Return a place for the scenario and its Ortsteil.

    Emergencies happen more often at places than at a door picked at random, so a share of the
    scenarios, as the settings say, happens at a named place of a kind people gather at: a station,
    a supermarket, a school, a park. Such a place gets the address of the nearest door, within a
    Bezirk setting when one is made. The rest, or when no fitting place turns up, take a random
    address, and without the address list a random named place.
    """
    if zufall.random() * 100 < erzeugung.anteil_orte:
        am_platz = platz_mit_adresse(quellen, erzeugung, zufall)
        if am_platz is not None:
            return am_platz
    adresse = quellen.adresse(zufall, erzeugung.ortsteil, erzeugung.bezirk)
    if adresse is not None:
        return ort_aus(adresse), adresse["ortsteil"]
    platz = quellen.ort(zufall, erzeugung.ortsteil)
    if platz is None and (erzeugung.ortsteil or erzeugung.bezirk):
        raise NichtsZuZiehen("Im gewählten Gebiet gibt es keine Adresse und keinen Ort.")
    if platz is None:
        raise NichtsZuZiehen("Weder das Adressverzeichnis noch die Orte sind geladen.")
    return Ort(
        adresse=Adresse(ortsteil=platz["ortsteil"]),
        koordinaten=(platz["breite"], platz["laenge"]),
        objekt=platz["name"],
    ), platz["ortsteil"]


def platz_mit_adresse(
    quellen: Quellen, erzeugung: Erzeugung, zufall: random.Random
) -> tuple[Ort, str] | None:
    """Return a named place of a gathering kind with the nearest door's address, if one fits."""
    for _ in range(PLATZ_VERSUCHE):
        platz = quellen.ort(zufall, erzeugung.ortsteil, EINSATZORTE)
        if platz is None:
            return None
        tuer = quellen.naechste(platz["breite"], platz["laenge"])
        if tuer is None or (erzeugung.bezirk and tuer["bezirk"] != erzeugung.bezirk):
            continue
        ort = ort_aus(tuer)
        ort.koordinaten = (platz["breite"], platz["laenge"])
        ort.objekt = f"{platz['name']} ({platz['art']})"
        return ort, tuer["ortsteil"]
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


def person_ziehen(graph: Abfragegraph, endpunkt: Endpunkt, zufall: random.Random) -> Person:
    """Return the affected person: an age the code allows, a sex, and whether they call."""
    unten, oben = altersspanne(graph, endpunkt)
    alter = zufall.randint(unten, oben)
    text = pfadtext(graph, endpunkt)
    weiblich = bool(re.search(r"schwanger|geburt|frauen", text)) or zufall.random() < 0.5
    stillstand = (
        endpunkt.protokoll == "rd.09"
        or endpunkt.kategorie.startswith("RD1NC REA")
        or bool(STILLSTAND.search(text))
    )
    bewusstlos = stillstand or bool(BEWUSSTLOS.search(text))
    anrufer_selbst = (
        alter >= 14
        and not bewusstlos
        and not endpunkt.kategorie.startswith("RD1")
        and zufall.random() < 0.3
    )
    atemnot = bool(ATEMNOT.search(text))
    return Person(alter, weiblich, anrufer_selbst, stillstand, bewusstlos, atemnot)


def titel_von(graph: Abfragegraph, endpunkt: Endpunkt) -> str:
    """Return a scenario's name: the code's reason, or its protocol when the reason is the code."""
    if endpunkt.anlass and endpunkt.anlass != endpunkt.code:
        return endpunkt.anlass
    wahl = endpunkt.pfad[0]
    protokoll = graph.antwort(wahl.knoten, wahl.antwort or "")
    return f"{protokoll.label} ({endpunkt.code})" if protokoll else endpunkt.code


def generieren(
    graph: Abfragegraph, quellen: Quellen, erzeugung: Erzeugung, zufall: random.Random
) -> Szenario:
    """Make up one complete scenario that fits the settings."""
    endpunkt = endpunkt_ziehen(graph, erzeugung, zufall)
    ort, ortsteil = ort_ziehen(quellen, erzeugung, zufall)
    rd = endpunkt.fachrichtung == "rd"
    person = person_ziehen(graph, endpunkt, zufall) if rd else Person(0, False, False)
    antworten = eroeffnung(graph, endpunkt, person, zufall)
    for schritt in endpunkt.pfad:
        antwort = graph.antwort(schritt.knoten, schritt.antwort or "")
        antworten[schritt.knoten] = Wahl(
            antwort=schritt.antwort, label=antwort.label if antwort else None
        )
    betroffen = zufallsname(zufall, person.weiblich) if rd else ""
    anrufer_name = betroffen if person.anrufer_selbst else zufallsname(zufall)
    if rd:
        an_tuer = bool(ort.adresse.hausnummer) and not ort.objekt
        ort.geschoss = zufall.choice(GESCHOSSE) if an_tuer else ""
        ort.klingel = betroffen.split()[-1] if an_tuer else ""
    stimmungen = STIMMUNGEN[stufe(endpunkt.kategorie)]
    stimmung = zufall.choices(list(stimmungen), weights=list(stimmungen.values()))[0]
    return Szenario(
        abfrage_version=graph.meta.version,
        titel=f"{titel_von(graph, endpunkt)}, {ortsteil}",
        herkunft=Herkunft.GENERIERT,
        ort=ort,
        anrufer=anrufer_ziehen(zufall, anrufer_name),
        betroffener=Betroffener(name=betroffen) if rd else None,
        antworten=antworten,
        ziel=Ziel(knoten=endpunkt.knoten, code=endpunkt.code),
        rolle=Rolle(stimmung=stimmung),
    )
