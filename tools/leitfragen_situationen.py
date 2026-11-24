"""Derives the guidance questions for "Welche Situation trifft zu?" into `daten/leitfragen/`.

Each medical protocol asks which situation applies, and the most severe one that applies counts.
The severity of a situation is that of the worst code reachable from it. So a "Ja" to a situation
rules out only those no more severe and keeps every more severe one, which later questions still
ask about; a "Nein" takes the situation out. Situations of the same severity lead to the same
urgency, so a "Ja" rules them out too. That way the order of the questions never decides
which situation is correct, only how soon it is found: danger signs come first, then the rest by
severity. Situations that differ only by an age band, or by an addition such as a known heart
condition, share one question; the call-taker knows the age from the opening, and a closing
question (`ZUSATZ`) settles the addition. Recurring situations get a question as one asks a
caller (`FRAGEN`), the rest are asked by their label. Protocols with many situations open with a
choice (`VORAB`). Catch-all situations ("Unbekannter Zustand", "Andere Codes nicht zutreffend")
and the upgrade are chosen directly. The result is checked like the server checks it at start.
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import leitfragen
from abfrage import Abfragegraph, laden

WURZEL = Path(__file__).resolve().parent.parent
ZIEL = WURZEL / "daten" / "leitfragen" / "situationen.json"
STUFE = {"E": 6, "D": 5, "C": 4, "B": 3, "A": 2, "O": 1}
NUR_DIREKT = re.compile(
    r"^aufwertung$|^unbekannter zustand|andere codes nicht zutreffend|^ohne weitere angabe"
    r"|^fragliche lebensbedrohung"
)
ALTERSBAND = re.compile(
    r"(?<![Pp]uls)(?<![Pp]uls )\s*(?:[<≥>]\s*\d+|\d+\s*[–-]\s*\d+)(?=\s*(?:\(|$))"
)
KARTENZUSATZ = re.compile(
    r"\s*\((?:[a-z] bis [a-z](?:; [a-z] bis [a-z])?|keine omega-stufe)\)", re.I
)
ABKUERZUNGEN = {
    "HWS",
    "TIA",
    "CO",
    "CBRN",
    "AUM",
    "BMA",
    "VU",
    "II",
    "III",
    "IV",
    "SSW",
    "KOF",
    "RTW",
    "VIZ",
}
NOMEN = {
    "ABSENCE",
    "ANGRIFF",
    "ATEMSTILLSTAND",
    "ATEMZÜGEN",
    "ATMUNG",
    "BEWUSSTSEINSLAGE",
    "DEFIBRILLATOR",
    "EREIGNIS",
    "ERKRANKUNGEN",
    "FEHLGEBURT",
    "FEHLLAGE",
    "GEFAHRGUT",
    "GESCHWINDIGKEIT",
    "GESICHT",
    "HAUTFARBE",
    "HILFE",
    "HUND",
    "HÖHE",
    "INSEKTENSCHWARM",
    "KOMPLIKATIONEN",
    "KRAFTEINWIRKUNG",
    "KÖRPERÖFFNUNGEN",
    "LEBENSBEDROHUNG",
    "NABELSCHNURVORFALL",
    "PERSON",
    "SCHLAGANFALL",
    "SPEZIALKRÄFTE",
    "SPRACHSCHWIERIGKEITEN",
    "STURZ",
    "SUIZIDGEDANKEN",
    "TOD",
    "TOTGEBURT",
    "TRIMESTER",
    "UNFALLMECHANISMUS",
    "VERGIFTUNG",
    "ÜBERDOSIS",
}
KLEIN = {
    "AGONALE",
    "ALLGEMEINE",
    "ANDAUERNDER",
    "ATYPISCHER",
    "AUS",
    "BEVORSTEHENDE",
    "DROHENDE",
    "DURCH",
    "ERWARTETE",
    "ERWARTETER",
    "EXOTISCHES",
    "EXTREMER",
    "FOKALER",
    "FRAGLICHE",
    "GEFÄHRLICHE",
    "GEFÄHRLICHER",
    "GERINGER",
    "GERINGFÜGIGE",
    "GROSSER",
    "GRÖSSERES",
    "HOHER",
    "IMPLANTIERTER",
    "INEFFEKTIVE",
    "KOMPLETTE",
    "KÜNSTLICHEN",
    "MASSIVE",
    "MULTIPLE",
    "MÖGLICHERWEISE",
    "NICHT",
    "OBERFLÄCHLICHE",
    "OFFENSICHTLICH",
    "OFFENSICHTLICHER",
    "PERIPHERE",
    "POSTPARTALE",
    "PSYCHISCHE",
    "PSYCHISCHER",
    "SCHWACHE",
    "SCHWERE",
    "SPÄTEN",
    "STARKE",
    "SUIZIDGEFÄHRDET",
    "TEILWEISE",
    "TOTE",
    "TRAUMATISCHE",
    "UNGEFÄHRLICHE",
    "UNGEFÄHRLICHEN",
    "UNGEWISSE",
    "UNMITTELBAR",
    "VERMUTETES",
    "VERÄNDERTE",
    "ZENTRALE",
    "ZWISCHEN",
    "ÄLTERE",
}
ZEICHEN = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


@dataclass(frozen=True)
class Frage:
    """A question as one asks a caller, for situations whose label matches `muster`."""

    muster: str
    frage: str
    hinweis: str = ""
    gefahr: bool = False


@dataclass(frozen=True)
class Zusatz:
    """A closing question for situations that differ only by an addition to their label."""

    frage: str
    positiv: str
    negativ: str | None = None


@dataclass(frozen=True)
class Wahl:
    """An opening choice: each answer keeps the situations whose label matches its pattern."""

    id: str
    frage: str
    antworten: list[tuple[str, str]]


@dataclass(frozen=True)
class JaNein:
    """An opening yes/no question: "Ja" takes out what `nein` matches, "Nein" what `ja` matches."""

    id: str
    frage: str
    ja: str
    nein: str
    bleibt: str = ""


@dataclass
class Gruppe:
    """Situations asked with one question."""

    frage: str
    hinweis: str
    gefahr: bool
    kacheln: list[str] = field(default_factory=list)


FRAGEN = [
    Frage(
        r"^kreislaufstillstand|atemstillstand|agonal|ineffektive atmung",
        "Atmet die Person nicht oder nur schnappend?",
        "Schnappatmung zählt als Atemstillstand.",
        gefahr=True,
    ),
    Frage(r"^bewusstlos", "Ist die Person bewusstlos?", gefahr=True),
    Frage(
        r"^bewusstseinstrübung",
        "Ist die Person benommen, verwirrt oder schwer weckbar?",
        gefahr=True,
    ),
    Frage(
        r"^veränderte bewusstseinslage",
        "Verhält sich die Person plötzlich ganz anders oder ist sie verwirrt?",
        gefahr=True,
    ),
    Frage(
        r"^abnorme atmung|^atembeschwerden|^ansprechbar mit abnormer atmung",
        "Atmet die Person auffällig: sehr schnell, mühsam oder geräuschvoll?",
        gefahr=True,
    ),
    Frage(
        r"^sprachschwierigkeiten zwischen",
        "Kann die Person zwischen den Atemzügen nur wenige Wörter sprechen?",
        gefahr=True,
    ),
    Frage(
        r"^veränderte hautfarbe|^aschfahle oder graue",
        "Ist die Haut grau, aschfahl oder bläulich?",
        gefahr=True,
    ),
    Frage(r"^kaltschwei", "Ist die Haut kalt und schweißnass?", gefahr=True),
    Frage(
        r"^gefährliche blutung",
        "Spritzt das Blut oder lässt es sich nicht stillen?",
        "Gefährlich: spritzend, nicht zu stillen, oder an Hals, Brust, Bauch, Leiste.",
        gefahr=True,
    ),
    Frage(r"^starke blutung", "Blutet es stark?"),
    Frage(
        r"^möglicherweise gefährliche blutung",
        "Blutet es aus Kopf, Hals, Brust, Bauch oder Leiste?",
    ),
    Frage(r"^schwache blutung", "Blutet es nur leicht?"),
    Frage(r"^ungefährliche blutung", "Ist die Blutung klein und schon gestillt?"),
    Frage(r"^mehrere verletzte", "Sind mehrere Personen verletzt?"),
    Frage(r"^sturz aus extremer höhe", "Ist die Person aus mehr als 10 Metern gefallen?"),
    Frage(
        r"^sturz aus grosser höhe",
        "Ist die Person aus großer Höhe gefallen, etwa mehr als 2 Meter?",
    ),
    Frage(
        r"^verletzungen im brust- oder halsbereich",
        "Ist die Brust oder der Hals verletzt und hat die Person Atembeschwerden?",
    ),
    Frage(
        r"^möglicherweise gefährliche körperregion",
        "Sind Kopf, Hals, Brust, Bauch, Rücken oder Becken verletzt?",
    ),
    Frage(
        r"^markierte \(\*\) ungefährliche körperregion mit fehlstellung",
        "Steht ein Arm oder Bein schief ab?",
    ),
    Frage(r"^ungefährliche körperregion", "Sind nur Hände, Füße, Arme oder Beine verletzt?"),
    Frage(
        r"^neurologische symptome erwähnt",
        "Hat die Person Kribbeln, Taubheit oder kann sie etwas nicht bewegen?",
    ),
    Frage(r"^ältere \(", "Ist die Verletzung älter als 6 Stunden?"),
    Frage(r"^normale atmung", "Atmet die Person normal?"),
    Frage(
        r"^ohnmachtsanfall/-anfälle und ansprechbar",
        "War die Person kurz bewusstlos und ist jetzt wieder ansprechbar?",
    ),
    Frage(
        r"^herzinfarkt-/angina pectoris-vorgeschichte",
        "Hatte die Person schon einmal einen Herzinfarkt oder Angina Pectoris?",
    ),
    Frage(r"^kokainmissbrauch", "Hat die Person Kokain genommen?"),
    Frage(r"^soeben wiederbelebt", "Wurde die Person gerade wiederbelebt oder geschockt?"),
    Frage(
        r"^plötzlich aufgetretene sprach-",
        "Kann die Person plötzlich nicht mehr richtig sprechen, lesen oder schreiben?",
    ),
    Frage(
        r"^plötzlich aufgetretene schwäche oder taubheit",
        "Ist eine Körperseite plötzlich schwach oder taub?",
    ),
    Frage(
        r"^plötzlich aufgetretene lähmung",
        "Ist eine Körperseite plötzlich gelähmt oder hängt eine Gesichtshälfte?",
    ),
    Frage(
        r"^plötzlich aufgetretener verlust des gleichgewichts",
        "Hat die Person plötzlich das Gleichgewicht verloren "
        "oder kann sich nicht mehr koordiniert bewegen?",
    ),
    Frage(r"^plötzliche sehstörungen", "Sieht die Person plötzlich schlecht oder doppelt?"),
    Frage(
        r"^plötzlicher beginn starker kopfschmerzen",
        "Hat die Person plötzlich sehr starke Kopfschmerzen?",
    ),
    Frage(r"^schlaganfall-vorgeschichte", "Hatte die Person schon einmal einen Schlaganfall?"),
    Frage(
        r"^tia-vorgeschichte",
        "Hatte die Person schon einmal eine kurze Durchblutungsstörung im Gehirn (TIA)?",
    ),
    Frage(
        r"^brustschmerzen/beschwerden in der brust",
        "Hat die Person Schmerzen oder Druck in der Brust?",
    ),
    Frage(r"^unmittelbar bevorstehende geburt", "Kommt das Kind gleich, muss die Frau pressen?"),
    Frage(
        r"aortenaneurysma",
        "Ist eine Erweiterung der Hauptschlagader bekannt "
        "oder reißt der Schmerz durch Bauch oder Rücken?",
    ),
    Frage(
        r"^aufprall mit hoher geschwindigkeit",
        "War es ein Aufprall mit hoher Geschwindigkeit oder großer Wucht?",
    ),
    Frage(
        r"^ansprechbar und verhält sich normal",
        "Ist die Person ansprechbar und verhält sich normal?",
    ),
    Frage(r"^abnormes verhalten", "Verhält sich die Person seltsam?"),
    Frage(r"^diabetiker", "Hat die Person Diabetes?"),
    Frage(
        r"^schwangerschaft/postpartale eklampsie",
        "Ist die Person schwanger oder hat sie gerade entbunden?",
    ),
    Frage(
        r"^schlaganfall- oder gehirntumor",
        "Hatte die Person einen Schlaganfall oder einen Hirntumor?",
    ),
    Frage(
        r"^überdosis/vergiftung",
        "Hat die Person Medikamente oder Drogen in zu großer Menge genommen?",
    ),
    Frage(r"^atypischer krampfanfall", "Ist der Anfall anders als sonst bei der Person?"),
    Frage(
        r"^andauernder oder multiple",
        "Krampft die Person noch oder hatte sie mehrere Anfälle hintereinander?",
    ),
    Frage(r"^drohender krampfanfall", "Spürt die Person, dass gleich ein Anfall kommt?"),
    Frage(
        r"^fokaler/absence-krampfanfall \(ansprechbar",
        "Zuckt nur ein Körperteil oder starrt die Person kurz ins Leere, ist aber ansprechbar?",
    ),
    Frage(
        r"^fokaler/absence-krampfanfall \(nicht ansprechbar",
        "Zuckt nur ein Körperteil oder starrt die Person ins Leere und ist nicht ansprechbar?",
    ),
    Frage(
        r"^effektive atmung nicht überprüft",
        "Ist noch nicht geprüft, ob die Person nach dem Anfall richtig atmet?",
    ),
    Frage(r"^nicht mehr krampfend", "Ist der Anfall vorbei und atmet die Person wieder richtig?"),
    Frage(r"^treppe hinunterstürzen", "Ist die Person eine Treppe hinuntergestürzt?"),
    Frage(r"^allgemeine hilfe", "Braucht die Person nur Hilfe beim Aufstehen, ohne Verletzungen?"),
    Frage(r"^bauchschmerzen$", "Hat die Person Bauchschmerzen?"),
    Frage(
        r"^nicht traumatische hoden", "Hat ein Mann ohne Verletzung Schmerzen in Hoden oder Leiste?"
    ),
    Frage(
        r"^frauen mit ohnmacht", "Ist eine Frau zwischen 12 und 50 umgekippt oder fast umgekippt?"
    ),
    Frage(r"^ohnmacht oder beinahe-ohnmacht", "Ist die Person umgekippt oder fast umgekippt?"),
    Frage(
        r"^männer mit schmerzen oberhalb", "Hat ein Mann ab 35 Schmerzen oberhalb des Bauchnabels?"
    ),
    Frage(
        r"^frauen mit schmerzen oberhalb", "Hat eine Frau ab 45 Schmerzen oberhalb des Bauchnabels?"
    ),
    Frage(
        r"^frauen mit schmerzen in der schulterspitze",
        "Hat eine Frau zwischen 12 und 50 Schmerzen in der Schulterspitze?",
    ),
    Frage(r"^frauen 12–50 mit bauchschmerzen", "Hat eine Frau zwischen 12 und 50 Bauchschmerzen?"),
    Frage(r"^bluter", "Ist die Person Bluter?"),
    Frage(r"^blutverdünnende medikamente", "Nimmt die Person blutverdünnende Medikamente?"),
    Frage(
        r"^blutungen aus künstlichen", "Blutet es aus einem künstlichen Ausgang, etwa einem Stoma?"
    ),
    Frage(r"^blutung aus dialyseshunt", "Blutet es aus dem Dialyse-Shunt?"),
    Frage(r"^blutungen aus krampfadern", "Blutet es aus einer Krampfader?"),
    Frage(
        r"^primäre postpartale blutung",
        "Blutet die Frau innerhalb von 24 Stunden nach der Geburt?",
    ),
    Frage(
        r"^sekundäre postpartale blutung",
        "Blutet die Frau mehr als 24 Stunden nach der Geburt?",
    ),
    Frage(
        r"^unbekannte körperregion",
        "Weiß der Anrufer nicht, wo die Person verletzt ist, weil er nicht bei ihr ist?",
    ),
    Frage(r"^amputation", "Ist ein Körperteil abgetrennt?"),
]
ZUSATZ = [
    Zusatz(
        "Ist ein Herzleiden bekannt?", r"mit bekanntem herzleiden", r"ohne bekanntes herzleiden"
    ),
    Zusatz(
        "Ist eine psychische Erkrankung bekannt?",
        r"\(vorgeschichte psychischer",
        r"keine oder unbekannte vorgeschichte",
    ),
    Zusatz(
        "Hat die Person Medikamente, Drogen oder andere Substanzen genommen?",
        r"\(einnahme von medikamenten",
    ),
    Zusatz(
        "Hat sich das Verhalten plötzlich verändert?", r"\(plötzliche veränderung des verhaltens"
    ),
    Zusatz(
        "Ist bei der Person eine Epilepsie bekannt?",
        r"\(bekannte epilepsie\)",
        r"keine epilepsie bestätigt",
    ),
]
ZUSATZKLAMMER = re.compile(
    r"\s*\((?:mit bekanntem|ohne bekanntes) herzleiden\)"
    r"|\s*\((?:keine oder unbekannte )?vorgeschichte psychische[rn]? erkrankungen\)"
    r"|\s*\(einnahme von medikamenten/substanzen\)"
    r"|\s*\(plötzliche veränderung des verhaltens/der persönlichkeit\)"
)
VORAB: dict[str, list[Wahl | JaNein]] = {
    "rd.22.k0": [
        Wahl(
            "wo",
            "Wo ist die Person eingeklemmt oder verschüttet?",
            [
                (
                    "In einem eingestürzten Gebäude oder einer Raumenge",
                    r"einsturz - gebäude|bauwerkeinsturz|raumenge",
                ),
                (
                    "In einem Graben, Erdfall, einer Lawine oder unwegsamem Gelände",
                    r"graben|erdfall|lawine|unzugängliches",
                ),
                ("Im Kofferraum oder unter einem Fahrzeug", r"kofferraum|unter fahrzeug"),
                ("Ein Körperteil steckt irgendwo fest", r"^eingeklemmt / eingeschlossen"),
                ("Nicht mehr eingeklemmt", r"^nicht mehr"),
            ],
        ),
        JaNein(
            "bestaetigt",
            "Steht fest, dass dort jemand eingeklemmt oder verschüttet ist?",
            ja=r"(?<!un)bestätigt",
            nein=r"unbestätigt",
        ),
        Wahl(
            "koerperteil",
            "Welcher Körperteil steckt fest?",
            [
                ("Finger, Zehe oder Haare", r"finger, zehe"),
                ("Hand, Fuß, Unterarm oder Unterschenkel", r"\(hand, handgelenk"),
                ("Kopf, Rumpf, Oberarm, Oberschenkel oder der ganze Körper", r"ganzer körper"),
            ],
        ),
        JaNein(
            "schwer",
            "Ist die Person schwer verletzt?",
            ja=r"mit schwerwiegenden|schwerwiegenden verletzungen",
            nein=r"nichtschwerwiegend|keine verletz|nicht gefährdet|keinen offensichtlichen",
            bleibt=r"oder unbekanntem körperteil|oder schwerwiegenden verletzungen",
        ),
    ],
    "rd.26.k0": [
        Wahl(
            "worum",
            "Worum geht es vor allem?",
            [
                (
                    "Fieber oder Infekt",
                    r"fieber|meningitis|halsentzündung|infizierte wunde|hepatitis"
                    r"|geschlechtsverkehr|furunkel",
                ),
                (
                    "Magen, Darm oder Blase",
                    r"übelkeit|erbrechen|verstopfung|stuhlabgang|darmeinlauf|urin|katheter|wasserlassen|hämorrhoiden",
                ),
                (
                    "Schmerzen",
                    r"andere schmerzen|ohrenschmerzen|zahnschmerzen|gicht"
                    r"|krämpfe/spasmen|penisprobleme",
                ),
                ("Haut", r"ausschlag|juckreiz|beulen|furunkel"),
                (
                    "Schwäche, Schwindel oder schlechter Zustand",
                    r"schwindel|reduzierter allgemeinzustand|unbeweglichkeit|schlecht/krank"
                    r"|blutdruck|keine notfallleitsymptome",
                ),
                ("Etwas steckt fest oder wurde verschluckt", r"objekt|fingerringe"),
                (
                    "Etwas anderes",
                    r"schlafstörungen|nervosität|schluckauf|taubheit|sichelzellen|dysreflexie|nebenniere"
                    r"|nur transportanforderung",
                ),
            ],
        ),
    ],
}


def kennung(text: str) -> str:
    """Return a question id from a text: lower case, umlauts spelled out, words joined by dashes."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower().translate(ZEICHEN))[:48].strip("-")


def schluessel(label: str) -> str:
    """Return what situations sharing one question have in common: the label without age band."""
    return ZUSATZKLAMMER.sub("", ALTERSBAND.sub("", label.lower())).strip()


def lesbar(label: str) -> str:
    """Return a situation's label as it reads in a question.

    Without age band and card notation; the words the card writes in capitals are spelled as
    usual, nouns with a capital letter (`NOMEN`), the rest small (`KLEIN`), abbreviations as they
    are. A capital word in neither list stops the tool, so no misspelling slips through.
    """
    text = KARTENZUSATZ.sub("", ALTERSBAND.sub("", label)).replace("eingeklemmmt", "eingeklemmt")

    def schreibung(treffer: re.Match[str]) -> str:
        wort = treffer.group(0)
        if wort in ABKUERZUNGEN:
            return wort
        if wort in NOMEN:
            return wort.capitalize()
        if wort in KLEIN:
            return wort.lower()
        raise ValueError(f"Schreibung unbekannt: {wort} in „{label}“")

    text = re.sub(r"\b[A-ZÄÖÜ]{2,}\b", schreibung, text)
    return text[:1].upper() + text[1:]


def frage_zu(label: str) -> Frage:
    """Return the question for a situation: a curated one, else one asking by its label."""
    klein = label.lower()
    for frage in FRAGEN:
        if re.search(frage.muster, klein):
            return frage
    return Frage("", f"Trifft das zu: {lesbar(label)}?")


def stufen(graph: Abfragegraph, knoten: str) -> dict[str, int]:
    """Return, per situation, the severity of the worst code reachable from it.

    The question graph has no cycles; should one appear, a node already on the way counts as
    nothing and the value found there is not remembered, so no value too low is kept.
    """
    gemerkt: dict[str, int] = {}

    def schwerste(ziel: str, unterwegs: frozenset[str]) -> tuple[int, bool]:
        if ziel in gemerkt:
            return gemerkt[ziel], True
        k = graph.knoten.get(ziel)
        if k is None:
            return 0, True
        if ziel in unterwegs:
            return 0, False
        if k.code:
            wert, vollstaendig = (STUFE.get(k.code[2], 0) if len(k.code) > 2 else 0), True
        else:
            ziele = [a.ziel for a in k.antworten or []]
            ziele += [k.ziel] if k.ziel else []
            ziele += list(k.weiche.ziele.values()) if k.weiche else []
            teile = [schwerste(z, unterwegs | {ziel}) for z in ziele]
            wert = max((w for w, _ in teile), default=0)
            vollstaendig = all(v for _, v in teile)
        if vollstaendig:
            gemerkt[ziel] = wert
        return wert, vollstaendig

    return {
        a.id: schwerste(a.ziel, frozenset({knoten}))[0]
        for a in graph.knoten[knoten].antworten or []
    }


def janein(id_: str, frage: str, ja: dict, nein: dict, hinweis: str = "") -> dict:
    """Return a question with a "Ja", a "Nein" and a "Weiß nicht"."""
    eintrag = {
        "id": id_,
        "frage": frage,
        "antworten": [{"label": "Ja", **ja}, {"label": "Nein", **nein}, {"label": "Weiß nicht"}],
    }
    if hinweis:
        eintrag["hinweis"] = hinweis
    return eintrag


def gruppenfrage(
    gruppe: Gruppe, stufe: dict[str, int], gefragt: list[str], direkt: list[str], id_: str
) -> dict:
    """Return the question of a group.

    "Ja" takes out what is no more severe, as situations of the same severity lead to the same
    urgency, and the situations chosen only directly, which a known situation rules out; "Nein"
    takes out the group.
    """
    unterste = min(stufe[k] for k in gruppe.kacheln)
    leichter = [k for k in gefragt if stufe[k] <= unterste and k not in gruppe.kacheln]
    ja = {"nimmt": leichter + direkt} if leichter or direkt else {}
    return janein(id_, gruppe.frage, ja, {"nimmt": gruppe.kacheln}, gruppe.hinweis)


def vorabfragen(knoten: str, kacheln: list[tuple[str, str]], stufe: dict[str, int]) -> list[dict]:
    """Return a protocol's opening questions; a choice keeps what is more severe than it."""
    fragen = []
    for vorab in VORAB.get(knoten, []):
        if isinstance(vorab, Wahl):
            antworten = []
            for text, muster in vorab.antworten:
                treffer = [t for t, label in kacheln if re.search(muster, label.lower())]
                if not treffer:
                    continue
                unterste = min(stufe[t] for t in treffer)
                schwerer = [t for t, _ in kacheln if stufe[t] > unterste and t not in treffer]
                antworten.append({"label": text, "behaelt": treffer + schwerer})
            fragen.append(
                {
                    "id": vorab.id,
                    "frage": vorab.frage,
                    "antworten": [*antworten, {"label": "Weiß nicht"}],
                }
            )
        else:
            ja = [t for t, label in kacheln if re.search(vorab.ja, label.lower())]
            nein = [t for t, label in kacheln if re.search(vorab.nein, label.lower())]
            bleibt = {
                t for t, label in kacheln if vorab.bleibt and re.search(vorab.bleibt, label.lower())
            }
            fragen.append(
                janein(
                    vorab.id,
                    vorab.frage,
                    {"nimmt": nein},
                    {"nimmt": [t for t in ja if t not in bleibt]},
                )
            )
    return fragen


def zusatzfragen(kacheln: list[tuple[str, str]]) -> list[dict]:
    """Return the closing questions for situations that differ only by an addition."""
    fragen = []
    for zusatz in ZUSATZ:
        ja = [t for t, label in kacheln if re.search(zusatz.positiv, label.lower())]
        if not ja:
            continue
        nein = [
            t for t, label in kacheln if zusatz.negativ and re.search(zusatz.negativ, label.lower())
        ]
        if nein:
            erste = {"nimmt": nein}
        else:
            ohne = [
                t for t, label in kacheln if t not in ja and not ZUSATZKLAMMER.search(label.lower())
            ]
            erste = {"behaelt": ja + ohne}
        fragen.append(janein(kennung(zusatz.frage), zusatz.frage, erste, {"nimmt": ja}))
    return fragen


def baue(graph: Abfragegraph, knoten: str) -> dict:
    """Return the guidance questions of one situation question."""
    kacheln = [(a.id, a.label) for a in graph.knoten[knoten].antworten or []]
    nur_direkt = [t for t, label in kacheln if NUR_DIREKT.search(label.lower())]
    gefragt = [(t, label) for t, label in kacheln if t not in nur_direkt]
    stufe = stufen(graph, knoten)
    gruppen: dict[str, Gruppe] = {}
    nach_schluessel: dict[str, str] = {}
    for kachel, label in gefragt:
        frage = frage_zu(nach_schluessel.get(schluessel(label), label))
        nach_schluessel.setdefault(schluessel(label), label)
        gruppe = gruppen.setdefault(frage.frage, Gruppe(frage.frage, frage.hinweis, frage.gefahr))
        gruppe.kacheln.append(kachel)
    reihenfolge = sorted(
        gruppen.values(), key=lambda g: (not g.gefahr, -max(stufe[k] for k in g.kacheln))
    )
    ids = [t for t, _ in gefragt]
    genutzt: set[str] = set()
    fragen = []
    for gruppe in reihenfolge:
        fid = kennung(gruppe.kacheln[0])
        while fid in genutzt:
            fid += "-x"
        genutzt.add(fid)
        fragen.append((gruppe.gefahr, gruppenfrage(gruppe, stufe, ids, nur_direkt, fid)))
    gefahr = [f for ist, f in fragen if ist]
    uebrige = [f for ist, f in fragen if not ist]
    alle = [*gefahr, *vorabfragen(knoten, gefragt, stufe), *uebrige, *zusatzfragen(gefragt)]
    ergebnis: dict = {"knoten": knoten, "fragen": alle}
    if nur_direkt:
        ergebnis["nurDirekt"] = nur_direkt
    return ergebnis


def situationsknoten(graph: Abfragegraph) -> list[str]:
    """Return the medical "Welche Situation trifft zu?" nodes with a choice to make."""
    return sorted(
        k
        for k, n in graph.knoten.items()
        if k.startswith("rd.") and k.endswith(".k0") and len(n.antworten or []) > 1
    )


def katalog(graph: Abfragegraph) -> dict:
    """Return the catalogue for all situation questions."""
    return {"knoten": [baue(graph, knoten) for knoten in situationsknoten(graph)]}


def main() -> None:
    """Write the catalogue and check it, naming every fault."""
    graph = laden(WURZEL / "daten" / "abfrage")
    daten = katalog(graph)
    eintraege = leitfragen.Katalog.model_validate(daten).knoten
    fehler = leitfragen.katalogfehler(eintraege, graph)
    if fehler:
        sys.exit("\n".join(fehler))
    ZIEL.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(
        f"{len(eintraege)} Situationsfragen mit {sum(len(e.fragen) for e in eintraege)} Leitfragen"
    )


if __name__ == "__main__":
    main()
