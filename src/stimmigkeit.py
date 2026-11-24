"""Whether a scenario's parts fit together: who calls, where they are, what they can know.

The generator is meant to make only scenarios that hold together; a trainer may write one that
does not, on purpose. These checks find the combinations that do not fit and report them as
warnings, never as errors: a third-hand caller standing next to the patient, a caller in cardiac
arrest, CPR guidance for someone who is not there, a plate read from miles away.
"""

import re
from typing import TYPE_CHECKING

from abfrage import Abfragegraph, Endpunkt

if TYPE_CHECKING:
    from szenario import Szenario

SELBST = "1-hand-der-anrufer-ist-selbst-betroffen"
BEIM_BETROFFENEN = "2-hand-der-anrufer-ist-beim-betroffenen"
FUER_ANDERE = "3-hand-der-anrufer-meldet-fuer-andere"
GEHOERT = "4-hand-der-anrufer-hat-es-nur-gehoert"
AUTOMATISCH = "automatische-meldung"
VOR_ORT_JA = "ja-der-anrufer-ist-vor-ort"
WACH = "ja-wach-und-ansprechbar"

NICHT_DABEI = frozenset({FUER_ANDERE, GEHOERT, AUTOMATISCH})
AUTOMATISCHE_PROTOKOLLE = frozenset({"rd.34", "fw.brand.brandmeldeanlage"})
OHNE_WOHNUNG = frozenset(
    {"rd.29", "rd.34", "rd.14", "fw.th.verkehrsunfall", "fw.brand.fahrzeugbrand"}
)
OHNE_SELBST = re.compile(
    r"eingeklemmt|verschüttet|eingeschlossen|droht zu springen|gesprungen|im wasser|ertrink"
    r"|erhäng|strangul|schwerste|unbekannter zustand|totgeburt|tote? person"
)
NENNT_SELBST = re.compile(r"anrufer 1\. hand(?! oder)")
NENNT_SELBST_ODER_DABEI = re.compile(r"anrufer 1\. oder 2\. hand")
NIEMAND_DA = re.compile(r"keine verletzungen gemeldet \(unbestätigt|niemand vor ort")
BESTAETIGT = re.compile(r"verletzungen bestätigt|bestätigt für")
STILLSTAND = re.compile(r"^RD1NC (REA|NNAD)")


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


def stimmigkeitsmeldungen(graph: Abfragegraph, szenario: Szenario) -> list[str]:
    """Return what in a scenario does not fit together, as warnings to show the trainer."""
    antworten = szenario.antworten
    hand = (antworten.get("eroeffnung.hand") or _leer).antwort
    vor_ort = (antworten.get("eroeffnung.vor-ort") or _leer).antwort
    reaktion = (antworten.get("rd.reaktion") or _leer).antwort
    atmung = (antworten.get("rd.atmung") or _leer).antwort
    endpunkt = next((e for e in graph.endpunkte if e.knoten == szenario.ziel.knoten), None)
    text = pfadtext(graph, endpunkt) if endpunkt else ""
    protokoll = endpunkt.protokoll if endpunkt else ""
    kategorie = (graph.knoten.get(szenario.ziel.knoten) or _leer).kategorie or ""
    da = vor_ort == VOR_ORT_JA
    meldungen = []
    if hand in NICHT_DABEI and da:
        meldungen.append("3./4. Hand oder automatische Meldung, aber Anrufer vor Ort")
    if hand in (SELBST, BEIM_BETROFFENEN) and vor_ort is not None and not da:
        meldungen.append("1./2. Hand, aber Anrufer nicht vor Ort")
    if hand == SELBST and (
        (reaktion not in (None, WACH)) or atmung in ("atmet-nicht", "unbekannt")
    ):
        meldungen.append("1. Hand, aber nicht wach, nicht atmend oder Zustand unbekannt")
    alter_knoten = graph.meta.person.alter_knoten if graph.meta.person else "rd.alter"
    alter = alter_aus((antworten.get(alter_knoten) or _leer).wert or "")
    if hand == SELBST and (OHNE_SELBST.search(text) or (alter is not None and alter < 14)):
        meldungen.append("1. Hand bei einer Lage, in der niemand selbst anruft")
    if NENNT_SELBST.search(text) and hand not in (None, SELBST):
        meldungen.append("der Code nennt einen Anrufer 1. Hand, die Eröffnung nicht")
    if NENNT_SELBST_ODER_DABEI.search(text) and hand not in (None, SELBST, BEIM_BETROFFENEN):
        meldungen.append("der Code nennt einen Anrufer 1. oder 2. Hand, die Eröffnung nicht")
    stillstand = atmung == "atmet-nicht" or bool(STILLSTAND.match(kategorie))
    if stillstand and hand is not None and (hand != BEIM_BETROFFENEN or not da):
        meldungen.append("Stillstand oder Todeszeichen, aber Anrufer nicht 2. Hand vor Ort")
    if NIEMAND_DA.search(text) and da:
        meldungen.append("der Code sagt, niemand ist vor Ort, die Eröffnung sagt vor Ort")
    if szenario.ort.ohne_adresse is not None and vor_ort is not None and not da:
        meldungen.append("Anrufer ohne Adresse beschreibt die Umgebung, ist aber nicht vor Ort")
    if _tafel_gelesen(graph, szenario) and vor_ort is not None and not da:
        meldungen.append("Warntafel gelesen, aber Anrufer nicht vor Ort")
    if protokoll in OHNE_WOHNUNG and (szenario.ort.geschoss or szenario.ort.klingel):
        meldungen.append("Geschoss oder Klingel bei einer Lage auf der Straße oder am Wasser")
    if hand == AUTOMATISCH and protokoll not in AUTOMATISCHE_PROTOKOLLE:
        meldungen.append("automatische Meldung bei einer Lage, die keine Anlage meldet")
    return meldungen


class _Leer:
    """Stands in for an answer or node that is not there."""

    antwort = None
    kategorie = None
    wert = None


_leer = _Leer()


def alter_aus(text: str) -> int | None:
    """Return an age in years from typed text: its first number, months, weeks or days as 0."""
    zahl = re.search(r"\d+", text)
    if zahl is None:
        return None
    return 0 if re.search(r"\b(monat|woche|tag)", text, re.IGNORECASE) else int(zahl.group())


def _tafel_gelesen(graph: Abfragegraph, szenario: Szenario) -> bool:
    """Tell whether the scenario answers a plate question with a plate."""
    return any(
        (knoten := graph.knoten.get(kid)) is not None
        and knoten.eingabe is not None
        and knoten.eingabe.art == "warntafel"
        and bool(wahl.wert)
        for kid, wahl in szenario.antworten.items()
    )
