"""The Berlin address list: downloaded once, kept in SQLite, searched and drawn from locally.

The source is the city's address WFS: some 400 000 points with street, house number, postcode,
Ortsteil, Bezirk and official coordinates, under the Datenlizenz Deutschland Zero 2.0. It is not
committed and not part of the image. The server fetches it in the background the first time it
can and again once the copy is older than its refresh age; nothing about startup depends on it.
Until a download has finished, search finds nothing and the location is typed and set on the map.

The service is asked for EPSG:4326 and answers GeoJSON, whose points are (longitude, latitude);
they are stored as latitude and longitude. The loading follows alarmzettel's.
"""

import os
import random
import re
import sqlite3
import tempfile
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

DIENST = "https://gdi.berlin.de/services/wfs/adressen_berlin"
TYPNAME = "adressen_berlin:adressen_berlin"
FELDER = "str_name,hnr,hnr_zusatz,plz,ort_name,bez_name,geom"
SEITE = 20000

SCHEMA = """
CREATE TABLE adressen (
    strasse   TEXT NOT NULL,
    suche     TEXT NOT NULL,
    hnr       INTEGER NOT NULL,
    zusatz    TEXT NOT NULL,
    plz       TEXT NOT NULL,
    ortsteil  TEXT NOT NULL,
    bezirk    TEXT NOT NULL,
    breite    REAL NOT NULL,
    laenge    REAL NOT NULL
);
CREATE TABLE stand (geholt TEXT NOT NULL);
"""

INDIZES = """
CREATE INDEX adressen_suche ON adressen (suche, hnr);
CREATE INDEX adressen_ortsteil ON adressen (ortsteil);
CREATE INDEX adressen_bezirk ON adressen (bezirk);
"""

ANGEHAENGT = re.compile(r"^(?P<strasse>.*?)[\s,]+(?P<hnr>\d+\s*[a-zA-Z]?)$")
STRASSE_KURZ = re.compile(r"(?<=.)(str\.?|strasse)$", re.IGNORECASE)
MINDESTANTEIL = 0.5


class Adressen:
    """The downloaded address list and the questions put to it.

    Every method copes with the file not being there, because for the first minutes of a fresh
    installation it is not, and on a machine without a route to the outside it never will be.
    """

    def __init__(self, datei: Path, hoechstalter_tage: int = 30) -> None:
        """Keep the list in a file, fetching it again once older than the given days."""
        self.datei = datei
        self.hoechstalter = timedelta(days=hoechstalter_tage)
        self._merker: dict[object, Any] = {}
        self._merker_stempel: int | None = None

    @contextmanager
    def _lesen(self) -> Iterator[sqlite3.Connection | None]:
        """Open the list read-only, or yield nothing when there is none yet."""
        if not self.datei.is_file():
            yield None
            return
        verbindung = sqlite3.connect(f"file:{self.datei}?mode=ro", uri=True)
        verbindung.row_factory = sqlite3.Row
        try:
            yield verbindung
        finally:
            verbindung.close()

    def bestand(self) -> dict:
        """Return whether the list is there, how many addresses it holds and when it was fetched.

        An unreadable file counts as no list, so the next check loads a new one over it.
        """
        try:
            return self._bestand()
        except sqlite3.DatabaseError:
            return {"verfuegbar": False, "anzahl": 0, "stand": None}

    def _bestand(self) -> dict:
        """Read the list's size and age from the file."""
        with self._lesen() as verbindung:
            if verbindung is None:
                return {"verfuegbar": False, "anzahl": 0, "stand": None}
            anzahl = verbindung.execute("SELECT count(*) FROM adressen").fetchone()[0]
            zeile = verbindung.execute("SELECT geholt FROM stand").fetchone()
            return {
                "verfuegbar": anzahl > 0,
                "anzahl": anzahl,
                "stand": zeile["geholt"] if zeile else None,
            }

    def veraltet(self) -> bool:
        """Tell whether there is no list, or the one there is has passed its refresh age."""
        bestand = self.bestand()
        if not bestand["verfuegbar"] or not bestand["stand"]:
            return True
        return datetime.now(UTC) - datetime.fromisoformat(bestand["stand"]) > self.hoechstalter

    def suchen(self, text: str, grenze: int = 12) -> list[dict]:
        """Return what to offer for what has been typed so far.

        Without a house number these are streets, each listed once per postcode and Ortsteil it
        runs through, since a long street crosses several. With one they are doors, carrying the
        coordinates, so picking one settles the whole address. "Karl-Marx-Str 92" finds
        "Karl-Marx-Straße 92": a trailing "str" or "str." is read as "straße".
        """
        name, hnr = zerlegen(text)
        anfaenge = suchformen(name)
        if len(anfaenge[0]) < 2:
            return []
        with self._lesen() as verbindung:
            if verbindung is None:
                return []
            if not hnr:
                return strassen(verbindung, anfaenge, grenze)
            return tueren(verbindung, anfaenge, hnr, grenze)

    def zufall(self, zufall: random.Random, ortsteil: str = "", bezirk: str = "") -> dict | None:
        """Return a random address, optionally within an Ortsteil or a Bezirk.

        Without an area a random row id is looked up, which the list's own key answers at once;
        within an area the count is remembered until the list is replaced, and the draw walks the
        area's index only.
        """
        with self._lesen() as verbindung:
            if verbindung is None:
                return None
            if not ortsteil and not bezirk:
                hoechste = self._gemerkt(
                    "hoechste",
                    lambda: verbindung.execute("SELECT max(rowid) FROM adressen").fetchone()[0],
                )
                if not hoechste:
                    return None
                zeile = verbindung.execute(
                    "SELECT * FROM adressen WHERE rowid >= ? LIMIT 1", [zufall.randint(1, hoechste)]
                ).fetchone()
                return tuer(zeile) if zeile else None
            spalte, wert = ("ortsteil", ortsteil) if ortsteil else ("bezirk", bezirk)
            anzahl = self._gemerkt(
                (spalte, wert),
                lambda: verbindung.execute(
                    f"SELECT count(*) FROM adressen WHERE {spalte} = ?", [wert]
                ).fetchone()[0],
            )
            if anzahl == 0:
                return None
            zeile = verbindung.execute(
                f"SELECT * FROM adressen WHERE {spalte} = ? LIMIT 1 OFFSET ?",
                [wert, zufall.randrange(anzahl)],
            ).fetchone()
            return tuer(zeile) if zeile else None

    def _gemerkt(self, schluessel: object, berechnen: Callable[[], Any]) -> Any:
        """Return a value worked out from the list, remembered until the list file changes."""
        stempel = self.datei.stat().st_mtime_ns
        if self._merker_stempel != stempel:
            self._merker = {}
            self._merker_stempel = stempel
        if schluessel not in self._merker:
            self._merker[schluessel] = berechnen()
        return self._merker[schluessel]

    def gebiete(self) -> dict[str, list[str]]:
        """Return each Bezirk with its Ortsteile, both sorted, or nothing before the first load."""
        with self._lesen() as verbindung:
            if verbindung is None:
                return {}

            def lesen() -> dict[str, list[str]]:
                gebiete: dict[str, list[str]] = {}
                for zeile in verbindung.execute(
                    "SELECT DISTINCT bezirk, ortsteil FROM adressen ORDER BY bezirk, ortsteil"
                ):
                    gebiete.setdefault(zeile["bezirk"], []).append(zeile["ortsteil"])
                return gebiete

            return self._gemerkt("gebiete", lesen)

    def laden(
        self, client: httpx.Client | None = None, stopp: threading.Event | None = None
    ) -> int:
        """Fetch the whole list and replace the stored one with it; return how many were stored.

        The list is written to a file of its own beside the target and renamed into place, so a
        download that dies halfway, or a second one running at the same time, leaves the copy that
        was there intact and searchable. A download that brings back nothing, fewer addresses than
        the service says it has, or less than half of what is stored, replaces nothing. A set
        `stopp` ends the download after the page in hand.
        """
        self.datei.parent.mkdir(parents=True, exist_ok=True)
        griff, name = tempfile.mkstemp(
            prefix=self.datei.name + ".", suffix=".neu", dir=self.datei.parent
        )
        os.close(griff)
        neu = Path(name)
        try:
            anzahl, gemeldet = self._herunterladen(neu, client, stopp)
            self._pruefen(anzahl, gemeldet)
            os.replace(neu, self.datei)
            return anzahl
        finally:
            neu.unlink(missing_ok=True)

    def _herunterladen(
        self, neu: Path, client: httpx.Client | None, stopp: threading.Event | None
    ) -> tuple[int, int | None]:
        """Write every page into a new list; return its size and the size the service reported."""
        verbindung = sqlite3.connect(neu)
        try:
            verbindung.executescript(SCHEMA)
            anzahl, gemeldet, start = 0, None, 0
            with client or httpx.Client(timeout=180.0, follow_redirects=True) as klient:
                while True:
                    if stopp is not None and stopp.is_set():
                        raise LadenAbgebrochen
                    roh, zeilen, gemeldet = seite(klient, start)
                    verbindung.executemany(
                        "INSERT INTO adressen VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", zeilen
                    )
                    anzahl += len(zeilen)
                    start += roh
                    if roh < SEITE:
                        break
            verbindung.executescript(INDIZES)
            verbindung.execute("INSERT INTO stand VALUES (?)", (datetime.now(UTC).isoformat(),))
            verbindung.commit()
            return anzahl, gemeldet
        finally:
            verbindung.close()

    def _pruefen(self, anzahl: int, gemeldet: int | None) -> None:
        """Refuse a download too small to replace the list that is there."""
        if anzahl == 0:
            raise UnvollstaendigeListe("Der Dienst hat keine Adressen geliefert.")
        if gemeldet is not None and anzahl < gemeldet * (1 - 0.01):
            raise UnvollstaendigeListe(f"Geladen {anzahl} von gemeldeten {gemeldet} Adressen.")
        bisher = self.bestand()["anzahl"]
        if anzahl < bisher * MINDESTANTEIL:
            raise UnvollstaendigeListe(f"Geladen {anzahl}, bisher {bisher} Adressen.")


class UnvollstaendigeListe(Exception):
    """A download that would replace the stored list with a much smaller one."""


class LadenAbgebrochen(Exception):
    """A download stopped because the server is shutting down."""


def zerlegen(text: str) -> tuple[str, str]:
    """Split "Archenholdstr 21" into street and house number; a trailing word stays in the name."""
    treffer = ANGEHAENGT.match(text.strip())
    if not treffer:
        return text.strip(), ""
    return treffer.group("strasse").strip(), treffer.group("hnr")


def suchformen(name: str) -> list[str]:
    """Return the forms a street is searched by: as typed, and with a trailing "str." spelled out.

    "Karl-Marx-Str" is searched as "karl-marx-str" and "karl-marx-straße", so the abbreviation
    finds the street while "Str" alone still finds "Stralauer Allee".
    """
    getippt = name.strip().lower()
    ausgeschrieben = STRASSE_KURZ.sub("straße", getippt)
    return [getippt] if ausgeschrieben == getippt else [getippt, ausgeschrieben]


def praefix(anfaenge: list[str]) -> tuple[str, list[str]]:
    """Return a condition matching streets that start with any of the forms, using the index.

    A range on the search column uses its index where LIKE would not, and takes the typed text
    literally, so `%` and `_` are no wildcards.
    """
    bedingung = " OR ".join("(suche >= ? AND suche < ?)" for _ in anfaenge)
    werte = [wert for anfang in anfaenge for wert in (anfang, anfang + "\uffff")]
    return f"({bedingung})", werte


def hausnummer(roh: str) -> tuple[int | None, str]:
    """Split "28A" or "28 a" into the number and its upper-case suffix."""
    ziffern = re.match(r"\d+", roh.strip())
    if not ziffern:
        return None, ""
    return int(ziffern.group()), roh.strip()[ziffern.end() :].strip().upper()


def strassen(verbindung: sqlite3.Connection, anfaenge: list[str], grenze: int) -> list[dict]:
    """Return the streets starting with the text, once per postcode and Ortsteil."""
    bedingung, werte = praefix(anfaenge)
    zeilen = verbindung.execute(
        f"SELECT strasse, plz, ortsteil, bezirk FROM adressen WHERE {bedingung} "
        "GROUP BY strasse, plz, ortsteil ORDER BY strasse, plz LIMIT ?",
        [*werte, grenze],
    ).fetchall()
    return [
        {
            "beschriftung": f"{z['strasse']}, {z['plz']} {z['ortsteil']}",
            "strasse": z["strasse"],
            "hausnummer": "",
            "plz": z["plz"],
            "ortsteil": z["ortsteil"],
            "bezirk": z["bezirk"],
        }
        for z in zeilen
    ]


def tueren(
    verbindung: sqlite3.Connection, anfaenge: list[str], hnr: str, grenze: int
) -> list[dict]:
    """Return the addresses on streets starting with the text that carry the house number."""
    zahl, zusatz = hausnummer(hnr)
    bedingung, werte = praefix(anfaenge)
    bedingung += " AND hnr = ?"
    werte.append(zahl)
    if zusatz:
        bedingung += " AND zusatz = ?"
        werte.append(zusatz)
    zeilen = verbindung.execute(
        f"SELECT * FROM adressen WHERE {bedingung} ORDER BY strasse, zusatz, plz LIMIT ?",
        [*werte, grenze],
    ).fetchall()
    return [tuer(zeile) for zeile in zeilen]


def tuer(zeile: sqlite3.Row) -> dict:
    """Return one address with its coordinates and a label."""
    nummer = f"{zeile['hnr']}{zeile['zusatz']}"
    return {
        "beschriftung": f"{zeile['strasse']} {nummer}, {zeile['plz']} {zeile['ortsteil']}",
        "strasse": zeile["strasse"],
        "hausnummer": nummer,
        "plz": zeile["plz"],
        "ortsteil": zeile["ortsteil"],
        "bezirk": zeile["bezirk"],
        "breite": zeile["breite"],
        "laenge": zeile["laenge"],
    }


def seite(klient: httpx.Client, start: int) -> tuple[int, list[tuple], int | None]:
    """Fetch one page: how many features it held, its usable addresses, and the reported total."""
    antwort = klient.get(
        DIENST,
        params={
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "TYPENAMES": TYPNAME,
            "OUTPUTFORMAT": "application/json",
            "SRSNAME": "EPSG:4326",
            "PROPERTYNAME": FELDER,
            "COUNT": SEITE,
            "STARTINDEX": start,
        },
    )
    antwort.raise_for_status()
    daten = antwort.json()
    merkmale = daten.get("features", [])
    zeilen = [z for m in merkmale if (z := zeile_aus(m)) is not None]
    gemeldet = daten.get("numberMatched")
    return len(merkmale), zeilen, gemeldet if isinstance(gemeldet, int) else None


def zeile_aus(merkmal: dict) -> tuple | None:
    """Return a feature as a row, or nothing when it lacks a street, a number or a point."""
    eigenschaft = merkmal.get("properties") or {}
    punkt = (merkmal.get("geometry") or {}).get("coordinates")
    strasse = eigenschaft.get("str_name")
    hnr = eigenschaft.get("hnr")
    if not strasse or hnr is None or not punkt:
        return None
    return (
        strasse,
        strasse.lower(),
        int(hnr),
        (eigenschaft.get("hnr_zusatz") or "").strip().upper(),
        eigenschaft.get("plz") or "",
        eigenschaft.get("ort_name") or "",
        eigenschaft.get("bez_name") or "",
        float(punkt[1]),
        float(punkt[0]),
    )
