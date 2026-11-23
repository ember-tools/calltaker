"""The Berlin address list: downloaded once, kept in SQLite, searched and drawn from locally.

The source is the city's address WFS: some 400 000 points with street, house number, postcode,
Ortsteil, Bezirk and official coordinates, under the Datenlizenz Deutschland Zero 2.0. It is not
committed and not part of the image. The server fetches it in the background the first time it
can and again once the copy is older than its refresh age; nothing about startup depends on it.
Until a download has finished, search finds nothing and the location is typed and set on the map.

The service is asked for EPSG:4326 and answers GeoJSON, whose points are (longitude, latitude);
they are stored as latitude and longitude. The loading follows alarmzettel's.
"""

import math
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

import ungefaehr

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

ANGEHAENGT = re.compile(
    r"^(?P<strasse>.*?)[\s,]+(?P<hnr>\d+(?:\s*[a-zA-Z](?![a-zA-ZäöüÄÖÜß]))?)"
    r"(?:[\s,]+(?P<ort>\d{5}\b.*|[^\d\s,].*))?$"
)
WORT = re.compile(r"[^\wäöüß]+")
ORT_VORRAT = 1000
AEHNLICHE_UNTER = 3
NAECHSTE_METER = 150
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

        A place may follow to narrow the choice, as callers say it: after the house number
        ("Sieg 25 bies" finds Siegmarstraße 25 in Biesdorf), after a comma ("Siegmarstr,
        Biesdorf"), or as the last word when the whole text finds no street ("Sieg bies"). Every
        word of the place must begin a word of the postcode, Ortsteil or Bezirk.
        """
        lesarten = lesarten_von(text)
        for name, hnr, ort in lesarten:
            treffer = self._suchen(praefix(suchformen(name)), name, hnr, ort, grenze)
            if len(treffer) >= AEHNLICHE_UNTER:
                return treffer
            if treffer:
                return treffer + self._aehnliche(name, hnr, ort, grenze - len(treffer), treffer)
        for name, hnr, ort in lesarten:
            treffer = self._aehnliche(name, hnr, ort, grenze, [])
            if treffer:
                return treffer
        return []

    def _suchen(
        self, bedingung: tuple[str, list], name: str, hnr: str, ort: str, grenze: int
    ) -> list[dict]:
        """Return the streets or doors matching a condition, a house number and a place."""
        if len(suchformen(name)[0]) < 2:
            return []
        vorrat = ORT_VORRAT if ort else grenze
        with self._lesen() as verbindung:
            if verbindung is None:
                return []
            gefunden = (
                tueren(verbindung, bedingung, hnr, vorrat)
                if hnr
                else strassen(verbindung, bedingung, vorrat)
            )
        return [eintrag for eintrag in gefunden if passt_zum_ort(eintrag, ort)][:grenze]

    def _aehnliche(
        self, name: str, hnr: str, ort: str, grenze: int, schon: list[dict]
    ) -> list[dict]:
        """Return low-quality matches: streets spelled or sounding almost like the name typed.

        They are marked `ungefaehr`, so the views can set them apart from the real matches.
        """
        if grenze <= 0 or not self.datei.is_file():
            return []
        vorhanden = {eintrag["strasse"] for eintrag in schon}
        kandidaten = [
            strasse
            for strasse in ungefaehr.aehnliche(self._gemerkt("namen", self._namen), name)
            if strasse not in vorhanden
        ]
        if not kandidaten:
            return []
        bedingung = (f"strasse IN ({', '.join('?' * len(kandidaten))})", kandidaten)
        gefunden = self._suchen(bedingung, name, hnr, ort, grenze * 4)
        rang = {strasse: stelle for stelle, strasse in enumerate(kandidaten)}
        gefunden.sort(key=lambda eintrag: rang[eintrag["strasse"]])
        return [{**eintrag, "ungefaehr": True} for eintrag in gefunden[:grenze]]

    def _namen(self) -> list[ungefaehr.Name]:
        """Return every street name of the list, prepared for similar-name searches."""
        with self._lesen() as verbindung:
            if verbindung is None:
                return []
            zeilen = verbindung.execute("SELECT DISTINCT strasse FROM adressen").fetchall()
        return ungefaehr.namen(zeile[0] for zeile in zeilen)

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

    def naechste(self, breite: float, laenge: float, radius: float = NAECHSTE_METER) -> dict | None:
        """Return the address closest to a point within a radius in metres, or None."""
        grad_breite = radius / 111_320
        grad_laenge = radius / (111_320 * math.cos(math.radians(breite)))
        with self._lesen() as verbindung:
            if verbindung is None:
                return None
            zeilen = verbindung.execute(
                "SELECT * FROM adressen WHERE breite BETWEEN ? AND ? AND laenge BETWEEN ? AND ?",
                [
                    breite - grad_breite,
                    breite + grad_breite,
                    laenge - grad_laenge,
                    laenge + grad_laenge,
                ],
            ).fetchall()
        if not zeilen:
            return None
        naechste = min(
            zeilen,
            key=lambda z: (
                (z["breite"] - breite) ** 2
                + ((z["laenge"] - laenge) * math.cos(math.radians(breite))) ** 2
            ),
        )
        return tuer(naechste)

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


def lesarten_von(text: str) -> list[tuple[str, str, str]]:
    """Return the ways a text can be read as street, house number and place, likeliest first.

    A place follows the house number, or a comma; without either, the last word may be the place
    when the whole text names no street.
    """
    name, hnr, ort = zerlegen(text)
    if not hnr and not ort and "," in name:
        name, ort = (teil.strip() for teil in name.rsplit(",", 1))
    lesarten = [(name, hnr, ort)]
    if not hnr and not ort and " " in name.strip():
        kopf, letztes = name.strip().rsplit(" ", 1)
        lesarten.append((kopf, "", letztes))
    return lesarten


def zerlegen(text: str) -> tuple[str, str, str]:
    """Split "Archenholdstr 21 Plänterwald" into street, house number and place.

    Without a house number the whole text is the street, so "Straße des 17. Juni" stays whole.
    """
    treffer = ANGEHAENGT.match(text.strip())
    if not treffer:
        return text.strip(), "", ""
    return (
        treffer.group("strasse").strip(),
        treffer.group("hnr"),
        (treffer.group("ort") or "").strip(),
    )


def passt_zum_ort(eintrag: dict, ort: str) -> bool:
    """Tell whether each word of a place begins a word of the postcode, Ortsteil or Bezirk."""
    woerter = WORT.sub(
        " ", f"{eintrag['plz']} {eintrag['ortsteil']} {eintrag['bezirk']}".lower()
    ).split()
    return all(
        any(wort.startswith(teil) for wort in woerter)
        for teil in WORT.sub(" ", ort.lower()).split()
    )


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


def strassen(verbindung: sqlite3.Connection, auswahl: tuple[str, list], grenze: int) -> list[dict]:
    """Return the streets a condition selects, once per postcode and Ortsteil."""
    bedingung, werte = auswahl
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
    verbindung: sqlite3.Connection, auswahl: tuple[str, list], hnr: str, grenze: int
) -> list[dict]:
    """Return the addresses on the streets a condition selects that carry the house number."""
    zahl, zusatz = hausnummer(hnr)
    bedingung, werte = auswahl[0], list(auswahl[1])
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
