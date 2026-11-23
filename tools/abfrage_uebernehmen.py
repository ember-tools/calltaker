"""Converts alarmzettel's interrogation graph once into this project's own question graph.

Run once to seed `daten/abfrage/`, whose JSON files it replaces; from then on the graph belongs
to this project and is edited here. The conversion:

* puts the choice of the Fachrichtung first and merges the three openings of alarmzettel into one,
  so the opening nodes carry the same ids whatever Fachrichtung is chosen; a switch then leads
  into the medical opening or into the fire brigade's choice of protocol,
* drops the floor, doorbell and hazard questions, which belong to the location,
* gives every node a stable, readable id and every answer an id within its node,
* marks the ages an answer applies to, read from the age determinants of the labels,
* cleans texts: decodes HTML entities, collapses whitespace and turns a dash used as a
  Gedankenstrich into a colon.

Usage: python tools/abfrage_uebernehmen.py [sna-tree.json] [target folder]
"""

import html
import json
import re
import sys
import unicodedata
import urllib.request
from collections import deque
from pathlib import Path

ALARMZETTEL_STAND = "f7f0e751ce832d14cdbd7178cb4e86c692f5c115"
QUELLE_URL = (
    "https://raw.githubusercontent.com/rainbowdashlabs/alarmzettel/"
    f"{ALARMZETTEL_STAND}/frontend/public/sna-tree.json"
)
ZIEL = Path(__file__).resolve().parent.parent / "daten" / "abfrage"

EROEFFNUNG = {
    "Aus welcher Hand kommt die Meldung?": "eroeffnung.hand",
    "Ist der Anrufer vor Ort?": "eroeffnung.vor-ort",
    "Wie viele Personen sind betroffen?": "rd.anzahl",
    "Wie alt ist die betroffene Person?": "rd.alter",
    "Mann oder Frau?": "rd.geschlecht",
    "Reagiert die Person normal?": "rd.reaktion",
    "Atmet die Person normal?": "rd.atmung",
}
FALLEN_WEG = {"Geschoss und Name am Klingelschild?", "Gefahren an der Einsatzstelle?"}
PROTOKOLLWAHL = {
    "notf": "Welche Hauptbeschwerde liegt vor?",
    "brand": "Was brennt?",
    "th": "Welche Lage liegt vor?",
}
UMLAUTE = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"}
)
GEDANKENSTRICH = chr(0x2014)
ALTER_VERGLEICH = re.compile(r"(?<!Puls )(≥|<)\s?(\d{2})(?!\d)(?=\s*(\(|$))")
ALTER_IN_KLAMMERN = re.compile(r"\((≤|>)\s?(\d{1,2}),")
ALTERSSPANNEN = (
    (re.compile(r"(\d+) bis (\d+) Jahre"), lambda a, b: {"min": int(a), "max": int(b)}),
    (re.compile(r"zwischen (\d+) und (\d+) Jahren"), lambda a, b: {"min": int(a), "max": int(b)}),
    (re.compile(r"bis (\d+) Jahre"), lambda a: {"max": int(a)}),
    (re.compile(r"älter (\d+) Jahre"), lambda a: {"min": int(a) + 1}),
    (re.compile(r"bis \d+ Tage"), lambda: {"max": 0}),
)
SLUG_LAENGE = 40


def main() -> None:
    """Read the source, convert it and write the files."""
    quelle = sys.argv[1] if len(sys.argv) > 1 else None
    ziel = Path(sys.argv[2]) if len(sys.argv) > 2 else ZIEL
    try:
        dateien = umwandeln(laden(quelle))
        schreiben(ziel, dateien)
    except ZielNichtLeer as fehler:
        print(fehler, file=sys.stderr)
        sys.exit(1)
    print(f"{len(dateien)} Dateien nach {ziel} geschrieben")


class ZielNichtLeer(Exception):
    """A target folder that holds files but no question graph, which must not be overwritten."""


def schreiben(ziel: Path, dateien: dict[str, dict]) -> None:
    """Write the files into the target, replacing the graph there.

    Only an empty folder or one that already holds a graph (its `meta.json`) is written into, so a
    mistyped target never loses files that are not the graph's.
    """
    if ziel.exists() and any(ziel.iterdir()) and not (ziel / "meta.json").is_file():
        raise ZielNichtLeer(f"{ziel} ist nicht leer und enthält keinen Abfragegraphen")
    for alt in ziel.rglob("*.json"):
        alt.unlink()
    for name, knoten in dateien.items():
        datei = ziel / name
        datei.parent.mkdir(parents=True, exist_ok=True)
        inhalt = knoten if name == "meta.json" else {"knoten": knoten}
        datei.write_text(json.dumps(inhalt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def laden(quelle: str | None) -> dict:
    """Read alarmzettel's graph from a file, or from its fixed commit when no file is given."""
    if quelle:
        return json.loads(Path(quelle).read_text(encoding="utf-8"))
    with urllib.request.urlopen(QUELLE_URL) as antwort:
        return json.loads(antwort.read())


def umwandeln(baum: dict) -> dict[str, dict]:
    """Convert the whole graph into files by their path below the target folder."""
    knoten = baum["knoten"]
    einstiege = {d["id"]: d["einstieg"] for d in baum["disziplinen"]}
    wahlen = {
        disziplin: kette_bis(knoten, einstiege[disziplin], frage)
        for disziplin, frage in PROTOKOLLWAHL.items()
    }
    eroeffnung, rd_eroeffnung = eroeffnungsknoten(knoten, wahlen["notf"][0])
    dateien = {
        "meta.json": meta(baum),
        "eroeffnung.json": eroeffnung,
        "rd/eroeffnung.json": rd_eroeffnung,
    }
    vergeben: dict[str, str] = {}
    hauptbeschwerde = knoten[wahlen["notf"][1]]
    rd_wahl, rd_protokolle = protokollwahl(
        knoten, hauptbeschwerde, "rd", vergeben, nr_als_name=True
    )
    dateien["rd/eroeffnung.json"]["rd.hauptbeschwerde"] = rd_wahl
    for name, inhalt in rd_protokolle.items():
        dateien[f"rd/{name}.json"] = inhalt
    fw_antworten = []
    for disziplin in ("brand", "th"):
        wahl, protokolle = protokollwahl(
            knoten, knoten[wahlen[disziplin][1]], f"fw.{disziplin}", vergeben
        )
        fw_antworten.extend(wahl["antworten"])
        for name, inhalt in protokolle.items():
            dateien[f"fw/{disziplin}/{name}.json"] = inhalt
    dateien["fw/grund.json"] = {
        "fw.grund": {"frage": "Warum benötigen Sie die Feuerwehr?", "antworten": fw_antworten}
    }
    return dateien


def kette_bis(knoten: dict, start: str, frage: str) -> tuple[list[str], str]:
    """Follow an opening from its start to the protocol choice; return the chain and that node."""
    kette = []
    aktuell = start
    while knoten[aktuell].get("frage") != frage:
        kette.append(aktuell)
        eintrag = knoten[aktuell]
        aktuell = eintrag.get("ziel") or eintrag["antworten"][0]["ziel"]
    return kette, aktuell


def eroeffnungsknoten(knoten: dict, kette: list[str]) -> tuple[dict, dict]:
    """Build the shared opening and the medical opening from alarmzettel's medical chain."""
    gemeinsam = {
        "fachrichtung": {
            "frage": "Was ist jetzt der Grund Ihres Anrufes?",
            "hinweis": "Auswahl Fachrichtung!",
            "antworten": [
                {
                    "id": "rd",
                    "nr": "0",
                    "label": "Med. Notruf",
                    "farbe": "rd",
                    "ziel": "eroeffnung.hand",
                },
                {
                    "id": "fw",
                    "nr": "5",
                    "label": "Brandschutz / techn. Notruf",
                    "farbe": "fw",
                    "ziel": "eroeffnung.hand",
                },
            ],
        },
    }
    medizinisch = {}
    behalten = [k for k in kette if knoten[k].get("frage") not in FALLEN_WEG]
    ids = [EROEFFNUNG[knoten[k]["frage"]] for k in behalten]
    folge = {ids[i]: ids[i + 1] for i in range(len(ids) - 1)}
    folge["eroeffnung.vor-ort"] = "eroeffnung.weiche"
    folge[ids[-1]] = "rd.hauptbeschwerde"
    for alt, neu in zip(behalten, ids, strict=True):
        eintrag = eroeffnungseintrag(knoten[alt], folge[neu])
        (gemeinsam if neu.startswith("eroeffnung.") else medizinisch)[neu] = eintrag
    gemeinsam["eroeffnung.weiche"] = {
        "weiche": {"knoten": "fachrichtung", "ziele": {"rd": ids[2], "fw": "fw.grund"}},
    }
    return gemeinsam, medizinisch


def eroeffnungseintrag(alt: dict, ziel: str) -> dict:
    """Convert one opening question, every answer leading to the next question."""
    if "eingabe" in alt:
        eingabe = {k: v for k, v in alt["eingabe"].items() if k != "eigen"}
        return {"frage": text(alt["frage"]), "eingabe": text(eingabe), "ziel": ziel}
    antworten = antwortliste(alt["antworten"], lambda _: ziel)
    return {"frage": text(alt["frage"]), "antworten": antworten}


def protokollwahl(
    knoten: dict, wahl: dict, praefix: str, vergeben: dict, nr_als_name: bool = False
):
    """Convert a choice of protocol and every protocol below it, one file each."""
    antworten = []
    protokolle = {}
    slugs: set[str] = set()
    for alt in wahl["antworten"]:
        name = alt["nr"] if nr_als_name and alt.get("nr") else eindeutig(slug(alt["label"]), slugs)
        protokoll = f"{praefix}.{name}"
        inhalt = protokollknoten(knoten, alt["ziel"], protokoll, vergeben)
        protokolle[name] = inhalt
        antwort = {
            "label": text(alt["label"]),
            "ziel": vergeben[alt["ziel"]],
            "protokoll": protokoll,
        }
        if alt.get("nr"):
            antwort["nr"] = alt["nr"]
        antworten.append(antwort)
    eindeutige_ids(antworten)
    return {"frage": wahl["frage"], "antworten": antworten}, protokolle


def protokollknoten(knoten: dict, start: str, protokoll: str, vergeben: dict) -> dict:
    """Convert one protocol breadth first; a node already converted elsewhere keeps its id."""
    ids_im_protokoll: set[str] = set()
    zaehler = 0
    reihenfolge = []
    offen = deque([start])
    while offen:
        alt = offen.popleft()
        if alt in vergeben:
            continue
        eintrag = knoten[alt]
        if "code" in eintrag:
            vergeben[alt] = eindeutig(f"{protokoll}.{slug(eintrag['code'])}", ids_im_protokoll)
        else:
            vergeben[alt] = f"{protokoll}.k{zaehler}"
            zaehler += 1
        reihenfolge.append(alt)
        offen.extend(a["ziel"] for a in eintrag.get("antworten", []))
        if "ziel" in eintrag:
            offen.append(eintrag["ziel"])
    return {vergeben[alt]: protokolleintrag(knoten[alt], vergeben) for alt in reihenfolge}


def protokolleintrag(alt: dict, vergeben: dict) -> dict:
    """Convert one node inside a protocol."""
    if "code" in alt:
        return {
            k: text(alt[k])
            for k in ("code", "kategorie", "anlass", "stichwort")
            if alt.get(k) is not None
        }
    if "eingabe" in alt:
        eingabe = {k: v for k, v in alt["eingabe"].items() if k != "eigen"}
        return {
            "frage": text(alt["frage"]),
            "eingabe": text(eingabe),
            "ziel": vergeben[alt["ziel"]],
        }
    return {
        "frage": text(alt["frage"]),
        "antworten": antwortliste(alt["antworten"], lambda a: vergeben[a["ziel"]]),
    }


def antwortliste(antworten: list[dict], ziel_von) -> list[dict]:
    """Convert a list of answers, giving each an id unique within it and marking its ages."""
    neu = []
    for alt in antworten:
        antwort = {"label": text(alt["label"]), "ziel": ziel_von(alt)}
        if alt.get("aussage"):
            antwort["aussage"] = text(alt["aussage"])
        if alt.get("nr"):
            antwort["nr"] = alt["nr"]
        grenze = altersgrenze(alt["label"])
        if grenze:
            antwort["alter"] = grenze
        neu.append(antwort)
    eindeutige_ids(neu)
    return neu


def eindeutige_ids(antworten: list[dict]) -> None:
    """Give every answer of a list an id from its label, unique within the list, as first key."""
    vergeben: set[str] = set()
    for i, antwort in enumerate(antworten):
        id_ = eindeutig(slug(antwort["label"]) or f"a{i}", vergeben)
        antworten[i] = {"id": id_, **antwort}


def altersgrenze(label: str) -> dict | None:
    """Read the ages an answer applies to from an age determinant in its label.

    Spans in years or days (`13 bis 17 Jahre`, `älter 56 Jahre`, `bis 30 Tage`) come first, then a
    bound written as a comparison at the end of the label or before a bracket (`≥ 50`, `< 35`),
    then one at the start of a bracket (`(≤ 6, ...`). Comparisons with a unit or after `Puls` are
    not ages and are left alone.
    """
    for muster, grenze in ALTERSSPANNEN:
        treffer = muster.search(label)
        if treffer:
            return grenze(*treffer.groups())
    treffer = ALTER_VERGLEICH.search(label)
    if treffer:
        zahl = int(treffer.group(2))
        return {"min": zahl} if treffer.group(1) == "≥" else {"max": zahl - 1}
    treffer = ALTER_IN_KLAMMERN.search(label)
    if treffer:
        zahl = int(treffer.group(2))
        return {"max": zahl} if treffer.group(1) == "≤" else {"min": zahl + 1}
    return None


def slug(text_: str) -> str:
    """Turn a label into an id: lower case ASCII words joined by hyphens, cut at a word boundary."""
    flach = (
        unicodedata.normalize("NFKD", text_.translate(UMLAUTE)).encode("ascii", "ignore").decode()
    )
    ganz = re.sub(r"[^a-z0-9]+", "-", flach.lower()).strip("-")
    if len(ganz) <= SLUG_LAENGE:
        return ganz
    gekuerzt = ganz[: SLUG_LAENGE + 1]
    return gekuerzt[: gekuerzt.rfind("-")] if "-" in gekuerzt else ganz[:SLUG_LAENGE]


def eindeutig(basis: str, vergeben: set[str]) -> str:
    """Return the base, or the base with a number, that is not yet taken, and take it."""
    kandidat = basis
    zaehler = 2
    while kandidat in vergeben:
        kandidat = f"{basis}-{zaehler}"
        zaehler += 1
    vergeben.add(kandidat)
    return kandidat


def text(wert):
    """Clean a text, or every text of a dict, for display.

    HTML entities are decoded, runs of whitespace become one space, and a dash used as a
    Gedankenstrich, em dash or spaced en dash, becomes a colon. An unspaced en dash is a range and
    stays.
    """
    if isinstance(wert, dict):
        return {k: text(v) for k, v in wert.items()}
    if not isinstance(wert, str):
        return wert
    sauber = " ".join(html.unescape(wert).split())
    sauber = sauber.replace(f" {GEDANKENSTRICH} ", ": ").replace(" \u2013 ", ": ")
    return sauber.replace(GEDANKENSTRICH, "-")


def meta(baum: dict) -> dict:
    """Build the graph's meta file."""
    erfunden = next(d for d in baum["disziplinen"] if d["id"] == "brand")["hinweis"]
    return {
        "version": 1,
        "wurzel": "fachrichtung",
        "quelle": (
            f"Abgeleitet aus alarmzettel ({ALARMZETTEL_STAND[:12]}), "
            "dort aus den offenen Daten der "
            f"Berliner Feuerwehr, Stand {baum['stand']}."
        ),
        "hinweise": {
            "rd": (
                "Die Codes und Anlässe stammen aus den offenen Daten der Berliner Feuerwehr. Die "
                "Fragen der Eröffnung (Hand der Meldung, Anrufer vor Ort, Anzahl der Betroffenen, "
                "Alter, Geschlecht, Reaktion, Atmung) sind ergänzt."
            ),
            "fw": text(erfunden),
        },
        "notfallkategorien": baum["notfallkategorien"],
    }


if __name__ == "__main__":
    main()
