"""Hazardous goods by UN number, as `tools/un_nummern_uebernehmen.py` takes them from chemie.de.

A number can name several entries, one per class or state of the substance. The hazard number
(Kemler number) of an orange plate is given where the list has one.
"""

import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

TAFEL = re.compile(r"^(X?\d{2,3})?/\d{4}$")
GEFAHRENZAHL = re.compile(r"^X?\d{2,3}$")


class Stoff(BaseModel):
    """One entry of the list."""

    model_config = ConfigDict(extra="forbid")

    un: str = Field(pattern=r"^\d{4}$")
    gefahrenzahl: str
    klasse: str
    bezeichnung: str


def laden(verzeichnis: Path) -> list[Stoff]:
    """Read the list, or nothing when it has not been taken yet."""
    datei = verzeichnis / "un.json"
    if not datei.exists():
        return []
    return [Stoff.model_validate(eintrag) for eintrag in json.loads(datei.read_text("utf-8"))]


def herkunft(verzeichnis: Path) -> dict:
    """Return where the list comes from and under which licence."""
    datei = verzeichnis / "meta.json"
    return json.loads(datei.read_text("utf-8")) if datei.exists() else {}


def tafel(stoff: Stoff) -> str:
    """Return a plate as the plate question records it: "hazard number/UN number"."""
    return f"{stoff.gefahrenzahl}/{stoff.un}"


def mit_warntafel(stoffe: list[Stoff]) -> list[Stoff]:
    """Return the entries a vehicle can carry an orange plate with numbers for.

    Left out are entries without a single hazard number: none, "?" for goods that may not be
    carried, and combined values such as "30 + 33" that no plate shows.
    """
    return [stoff for stoff in stoffe if GEFAHRENZAHL.match(stoff.gefahrenzahl)]
