"""Named places of Berlin from OpenStreetMap: parks, stations, hospitals, allotment gardens.

The address list knows only doors. The places a caller names instead come from a file derived
from OpenStreetMap's Berlin extract (see `tools/orte_uebernehmen.py`), committed with the code and
held in memory, some 18 000 entries. A search matches every word typed in a place's name or
Ortsteil, with punctuation ignored, so "Lidl Neukölln" finds the Lidl stores in Neukölln. Places
whose name holds every word come first, then names starting with the text, then shorter names. A
missing or unreadable file, such as the pointer Git LFS leaves when its content was not fetched,
leaves the search empty and is logged, so the server starts without it.
"""

import gzip
import json
import logging
import random
import re
from collections.abc import Collection
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from geo import entfernung

WORT = re.compile(r"[^\w]+")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Ort:
    """One named place with its kind, Ortsteil and point."""

    name: str
    art: str
    ortsteil: str
    breite: float
    laenge: float
    suche: str
    ueberall: str

    def nach_aussen(self) -> dict:
        """Return the place as the views read it."""
        return {
            "beschriftung": f"{self.name} ({self.art}), {self.ortsteil}",
            "name": self.name,
            "art": self.art,
            "ortsteil": self.ortsteil,
            "breite": self.breite,
            "laenge": self.laenge,
        }


def suchform(text: str) -> str:
    """Return a text lower-cased, with punctuation as single spaces, as names are searched."""
    return " ".join(WORT.sub(" ", text.lower()).split())


class Orte:
    """The places of the derived file, and the search over them."""

    def __init__(self, verzeichnis: Path) -> None:
        """Read the places from a folder holding `orte.json.gz` and `meta.json`, if there."""
        roh = lesen(verzeichnis / "orte.json.gz")
        self.orte = [
            Ort(n, a, o, b, laenge, suchform(n), suchform(f"{n} {o}")) for n, a, o, b, laenge in roh
        ]
        meta = verzeichnis / "meta.json"
        self.meta = json.loads(meta.read_text(encoding="utf-8")) if meta.is_file() else {}

    def suchen(self, text: str, grenze: int = 6) -> list[dict]:
        """Return the places whose name or Ortsteil holds every word of the text, best first."""
        gesucht = suchform(text)
        woerter = gesucht.split()
        if len(gesucht) < 3:
            return []
        treffer = [ort for ort in self.orte if all(wort in ort.ueberall for wort in woerter)]
        treffer.sort(
            key=lambda ort: (
                not all(wort in ort.suche for wort in woerter),
                not ort.suche.startswith(gesucht),
                len(ort.suche),
                ort.suche,
            )
        )
        return [ort.nach_aussen() for ort in treffer[:grenze]]

    def zufall(
        self, zufall: random.Random, ortsteil: str = "", arten: Collection[str] = ()
    ) -> dict | None:
        """Return a random place, optionally within an Ortsteil and of some kinds, or None."""
        auswahl = [
            ort
            for ort in self.orte
            if (not ortsteil or ort.ortsteil == ortsteil) and (not arten or ort.art in arten)
        ]
        return zufall.choice(auswahl).nach_aussen() if auswahl else None

    def umkreis(self, breite: float, laenge: float, radius: float) -> list[dict]:
        """Return the places within a radius in metres of a point, nearest first."""
        nahe = [(entfernung((breite, laenge), (ort.breite, ort.laenge)), ort) for ort in self.orte]
        nahe = [(abstand, ort) for abstand, ort in nahe if abstand <= radius]
        nahe.sort(key=lambda paar: paar[0])
        return [ort.nach_aussen() for _, ort in nahe]


def lesen(datei: Path) -> list:
    """Read the places file, or nothing when it is missing or not a places file."""
    if not datei.is_file():
        logger.warning("Keine Orte: %s fehlt.", datei)
        return []
    try:
        return json.loads(gzip.decompress(datei.read_bytes()))
    except OSError, EOFError, ValueError:
        logger.warning("Keine Orte: %s ist keine Ortsdatei, fehlt `git lfs pull`?", datei)
        return []


@lru_cache
def orte_laden(verzeichnis: Path) -> Orte:
    """Return the places of a folder, read once per process."""
    return Orte(verzeichnis)
