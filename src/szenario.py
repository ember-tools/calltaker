"""Scenarios: the truth behind a call, and how a scenario is checked against the question graph.

A scenario's path through the graph is keyed by node id, not by order, so the answers to nodes the
trainee also visits stay valid when the trainee takes another turn. Field names follow the
frontend's camel case on the wire.
"""

import uuid
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from abfrage import Abfragegraph, Antwort
from gefahrstoffe import TAFEL
from geo import entfernung
from rufnummer import normalisieren
from stimmigkeit import alter_aus, stimmigkeitsmeldungen

SZENARIO_VERSION = 1


def neue_id() -> str:
    """Return a fresh scenario id."""
    return uuid.uuid4().hex


class Modell(BaseModel):
    """Base of the scenario models: camel case on the wire, unknown fields refused."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Adresse(Modell):
    """A postal address in Berlin."""

    strasse: str = ""
    hausnummer: str = ""
    plz: str = ""
    ortsteil: str = ""


class Umgebungsort(Modell):
    """A named place a caller without an address can see: where it lies from them, and how far."""

    name: str = Field(max_length=200)
    art: str = Field(max_length=80)
    richtung: str = Field(max_length=20)
    meter: int = Field(ge=0, le=5000)


class OhneAdresse(Modell):
    """A caller outside who does not know the address: what they are at and what they can see.

    `wo` is how they name the place they are at, by its name only when they know it.
    """

    wo: str = Field(max_length=200)
    umgebung: list[Umgebungsort] = Field(default_factory=list, max_length=5)


class Ort(Modell):
    """Where the emergency is: address, point and what a crew needs to find it.

    `koordinaten` is (latitude, longitude) in WGS 84, Leaflet's order, not GeoJSON's.
    """

    adresse: Adresse = Field(default_factory=Adresse)
    koordinaten: tuple[float, float] | None = None
    objekt: str = ""
    geschoss: str = ""
    klingel: str = ""
    anfahrt: str = ""
    gefahren: str = ""
    haustier: str = ""
    ohne_adresse: OhneAdresse | None = None


class Funkzelle(Modell):
    """The area the mobile cell a call comes through covers: a centre and a radius in metres."""

    mitte: tuple[
        Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)],
        Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)],
    ]
    radius: float = Field(gt=0, le=5000)


class Anrufer(Modell):
    """Who calls: the name, the number shown, and the number the caller is reachable under."""

    name: str
    rufnummer: str | None = None
    rufnummer_unterdrueckt: bool = False
    rueckrufnummer: str | None = None
    funkzelle: Funkzelle | None = None

    @field_validator("rufnummer", "rueckrufnummer")
    @classmethod
    def nur_ziffern(cls, wert: str | None) -> str | None:
        """Store numbers as digits with the country code, however they were typed."""
        return normalisieren(wert) or None if wert else None

    @model_validator(mode="after")
    def nummer_vorhanden(self) -> Self:
        """Require a shown number, or a callback number and no shown one when it is withheld."""
        if self.rufnummer_unterdrueckt and self.rufnummer:
            raise ValueError("eine unterdrückte Rufnummer wird nicht angezeigt")
        if self.rufnummer_unterdrueckt and not self.rueckrufnummer:
            raise ValueError("bei unterdrückter Rufnummer ist eine Rückrufnummer Pflicht")
        if not self.rufnummer_unterdrueckt and not self.rufnummer:
            raise ValueError("ohne Unterdrückung ist eine Rufnummer Pflicht")
        return self

    def mobil_angezeigt(self) -> bool:
        """Tell whether the call shows a mobile number, which a cell can be given for."""
        return not self.rufnummer_unterdrueckt and (self.rufnummer or "").startswith("491")

    def erreichbar_unter(self) -> str:
        """Return the number the caller can actually be called back on."""
        return self.rueckrufnummer or self.rufnummer or ""


class Betroffener(Modell):
    """The person the call is about, when it is not the caller."""

    name: str = ""


class Wahl(Modell):
    """What the caller answers at one node: an answer id, or a typed value.

    `label` keeps the answer's label as it read when the scenario was written, so a later change
    of the graph can be pointed out.
    """

    antwort: str | None = None
    label: str | None = None
    wert: str | None = None


class Ziel(Modell):
    """The endpoint the scenario's path ends in, by node, with its code for reading."""

    knoten: str
    code: str


class Rolle(Modell):
    """How the trainer plays the caller; not part of the debrief."""

    stimmung: Literal["ruhig", "aufgeregt", "panisch", "verwirrt"] | None = None
    sprache: str = ""
    notizen: str = ""


class Herkunft(StrEnum):
    """Whether a scenario was written by hand or generated."""

    VORBEREITET = "vorbereitet"
    GENERIERT = "generiert"


class Szenario(Modell):
    """The truth behind one call."""

    id: str = Field(default_factory=neue_id)
    version: Literal[1] = SZENARIO_VERSION
    abfrage_version: int
    titel: str
    herkunft: Herkunft = Herkunft.VORBEREITET
    ort: Ort
    anrufer: Anrufer
    betroffener: Betroffener | None = None
    antworten: dict[str, Wahl] = Field(default_factory=dict)
    ziel: Ziel
    rolle: Rolle = Field(default_factory=Rolle)
    erweiterungen: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def passende_ortsangabe(self) -> Self:
        """Drop the description of a caller without an address once the place has an address.

        An edited scenario that gets a street, or loses its point, no longer fits what the caller
        was made up to see.
        """
        if self.ort.ohne_adresse is not None and (
            self.ort.adresse.strasse or self.ort.koordinaten is None
        ):
            self.ort.ohne_adresse = None
        return self

    @model_validator(mode="after")
    def passende_funkzelle(self) -> Self:
        """Drop a cell that does not fit: no shown mobile number, or the place lies outside it.

        A scenario edited after it was made can change the number or the place; the cell then
        no longer tells the truth and is left out rather than misleading the trainee.
        """
        zelle = self.anrufer.funkzelle
        if zelle is None:
            return self
        punkt = self.ort.koordinaten
        if (
            not self.anrufer.mobil_angezeigt()
            or punkt is None
            or entfernung(zelle.mitte, punkt) > zelle.radius
        ):
            self.anrufer.funkzelle = None
        return self

    def nach_aussen(self) -> dict:
        """Return the scenario as the frontend and the pool file carry it."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class Befund(Modell):
    """One thing a check found: an error to correct, or a warning to look at."""

    art: Literal["fehler", "warnung"]
    knoten: str | None = None
    meldung: str

    def nach_aussen(self) -> dict:
        """Return the finding as the frontend reads it."""
        return self.model_dump(by_alias=True, exclude_none=True)


def pruefen(szenario: Szenario, graph: Abfragegraph) -> list[Befund]:
    """Check a scenario against the current graph and return what does not fit."""
    befunde: list[Befund] = []
    if szenario.abfrage_version != graph.meta.version:
        befunde.append(
            Befund(
                art="warnung",
                meldung=(
                    f"geschrieben für Abfragegraph {szenario.abfrage_version}, "
                    f"aktuell ist {graph.meta.version}"
                ),
            )
        )
    for knoten_id, wahl in szenario.antworten.items():
        befunde.extend(wahlbefunde(graph, knoten_id, wahl))
    befunde.extend(zielbefunde(graph, szenario.ziel))
    befunde.extend(personbefunde(graph, szenario.antworten))
    befunde.extend(
        Befund(art="warnung", meldung=meldung) for meldung in stimmigkeitsmeldungen(graph, szenario)
    )
    return befunde


def personbefunde(graph: Abfragegraph, antworten: dict[str, Wahl]) -> list[Befund]:
    """Warn about answers that do not fit the age or sex the same scenario gives.

    The questioning answers such nodes itself from age and sex, so a contradicting answer would
    send the trainee another way than the truth, as older scenarios can.
    """
    person = graph.meta.person
    if person is None:
        return []
    alter_wahl = antworten.get(person.alter_knoten)
    unbekannt = alter_wahl is not None and not (alter_wahl.wert or "").strip()
    alter = alter_aus(alter_wahl.wert) if alter_wahl and alter_wahl.wert else None
    geschlecht_wahl = antworten.get(person.geschlecht_knoten)
    geschlecht = person.geschlecht.get(geschlecht_wahl.antwort or "") if geschlecht_wahl else None
    befunde = []
    for knoten_id, wahl in antworten.items():
        antwort = graph.antwort(knoten_id, wahl.antwort or "")
        if antwort is None:
            continue
        grund = widerspruch(antwort, alter, unbekannt, geschlecht)
        if grund:
            befunde.append(Befund(art="warnung", knoten=knoten_id, meldung=grund))
    return befunde


def spanne(unten: int | None, oben: int | None) -> str:
    """Return age bounds as read aloud: "ab 13 Jahren", "bis 12 Jahre", "für 12 bis 50 Jahre"."""
    if oben is None:
        return f"ab {unten} Jahren"
    if unten is None:
        return f"bis {oben} Jahre"
    return f"für {unten} bis {oben} Jahre"


def widerspruch(
    antwort: Antwort, alter: int | None, unbekannt: bool, geschlecht: str | None
) -> str:
    """Return why an answer contradicts the person, or an empty text."""
    grenze = antwort.alter
    if grenze is not None and grenze.unbekannt and alter is not None:
        return f"gilt für ein unbekanntes Alter, das Szenario nennt {alter}"
    if grenze is not None and not grenze.unbekannt:
        if unbekannt:
            return "gilt für ein bestimmtes Alter, das Szenario lässt es offen"
        unten = grenze.min if grenze.min is not None else 0
        oben = grenze.max if grenze.max is not None else 200
        if alter is not None and not unten <= alter <= oben:
            return f"gilt {spanne(grenze.min, grenze.max)}, das Szenario nennt {alter}"
    if antwort.geschlecht and geschlecht and antwort.geschlecht != geschlecht:
        return "gilt für ein anderes Geschlecht als im Szenario"
    return ""


def zielbefunde(graph: Abfragegraph, ziel: Ziel) -> list[Befund]:
    """Check that the scenario's endpoint exists and still carries its code."""
    knoten = graph.knoten.get(ziel.knoten)
    if knoten is None or knoten.code is None:
        return [Befund(art="fehler", knoten=ziel.knoten, meldung="Endpunkt gibt es nicht mehr")]
    if knoten.code != ziel.code:
        return [
            Befund(
                art="warnung",
                knoten=ziel.knoten,
                meldung=f"Endpunkt trägt jetzt Code {knoten.code} statt {ziel.code}",
            )
        ]
    return []


def wahlbefunde(graph: Abfragegraph, knoten_id: str, wahl: Wahl) -> list[Befund]:
    """Check the answer a scenario gives at one node."""
    knoten = graph.knoten.get(knoten_id)
    if knoten is None:
        return [Befund(art="fehler", knoten=knoten_id, meldung="Knoten gibt es nicht mehr")]
    if knoten.eingabe is not None:
        if wahl.antwort is not None:
            return [
                Befund(art="fehler", knoten=knoten_id, meldung="hier wird getippt, nicht gewählt")
            ]
        if not wahl.wert and knoten.eingabe.leer is None:
            return [Befund(art="fehler", knoten=knoten_id, meldung="hier fehlt der getippte Wert")]
        if knoten.eingabe.art == "warntafel" and wahl.wert and not TAFEL.match(wahl.wert):
            meldung = "eine Warntafel lautet Gefahrenzahl/UN-Nummer, z. B. 33/1203"
            return [Befund(art="fehler", knoten=knoten_id, meldung=meldung)]
        return []
    if knoten.antworten is None:
        return [
            Befund(art="fehler", knoten=knoten_id, meldung="an diesem Knoten wird nicht gefragt")
        ]
    if wahl.antwort is None:
        return [Befund(art="fehler", knoten=knoten_id, meldung="hier wird gewählt, nicht getippt")]
    antwort = graph.antwort(knoten_id, wahl.antwort)
    if antwort is None:
        return [
            Befund(
                art="fehler", knoten=knoten_id, meldung=f"Antwort {wahl.antwort} gibt es nicht mehr"
            )
        ]
    if wahl.label is not None and wahl.label != antwort.label:
        return [
            Befund(
                art="warnung",
                knoten=knoten_id,
                meldung=f"Antwort heißt jetzt „{antwort.label}“ statt „{wahl.label}“",
            )
        ]
    return []
