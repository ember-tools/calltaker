"""The pool of scenarios an exercise draws its calls from, and its file format."""

from typing import Literal

from pydantic import Field, ValidationError

from abfrage import Abfragegraph
from fehlermeldung import deutsch
from szenario import Befund, Modell, Szenario, neue_id, pruefen

POOL_FORMAT = "calltaker-pool"
POOL_VERSION = 1


class Pooldatei(Modell):
    """A downloaded pool, as it is uploaded again."""

    format: Literal["calltaker-pool"]
    version: Literal[1]
    abfrage_version: int
    szenarien: list[Szenario] = Field(default_factory=list)


class UngueltigeDatei(ValueError):
    """An uploaded file that is not a pool this version can read."""


class Pool:
    """The scenarios of one exercise, in the trainer's order."""

    def __init__(self) -> None:
        """Start with an empty pool."""
        self._szenarien: list[Szenario] = []

    @property
    def szenarien(self) -> list[Szenario]:
        """Return the scenarios in order."""
        return list(self._szenarien)

    def hinzufuegen(self, szenario: Szenario) -> Szenario:
        """Append a scenario; an id already in the pool gets a new one."""
        if self.finden(szenario.id) is not None:
            szenario = szenario.model_copy(update={"id": neue_id()})
        self._szenarien.append(szenario)
        return szenario

    def ersetzen(self, szenario: Szenario) -> None:
        """Replace the scenario with the same id."""
        self._szenarien[self._stelle(szenario.id)] = szenario

    def entfernen(self, szenario_id: str) -> Szenario:
        """Remove a scenario and return it."""
        return self._szenarien.pop(self._stelle(szenario_id))

    def verschieben(self, szenario_id: str, ziel: int) -> None:
        """Move a scenario to a position, clamped to the pool's bounds."""
        szenario = self._szenarien.pop(self._stelle(szenario_id))
        self._szenarien.insert(max(0, min(ziel, len(self._szenarien))), szenario)

    def finden(self, szenario_id: str) -> Szenario | None:
        """Return the scenario with the given id, if any."""
        return next((s for s in self._szenarien if s.id == szenario_id), None)

    def exportieren(self, graph: Abfragegraph) -> dict:
        """Return the pool as a file to download."""
        return {
            "format": POOL_FORMAT,
            "version": POOL_VERSION,
            "abfrageVersion": graph.meta.version,
            "szenarien": [s.nach_aussen() for s in self._szenarien],
        }

    def importieren(
        self, roh: object, modus: Literal["ersetzen", "anhaengen"], graph: Abfragegraph
    ) -> dict[str, list[Befund]]:
        """Take the scenarios of an uploaded file and return what the graph check found for each.

        A file that is not a pool, or holds a scenario that is not one, is refused as a whole and
        leaves the pool as it was. A scenario that refers to nodes the graph no longer has is
        taken all the same, so the trainer can correct it in the editor.
        """
        datei = lesen(roh)
        if modus == "ersetzen":
            self._szenarien = []
        befunde = {}
        for szenario in datei.szenarien:
            aufgenommen = self.hinzufuegen(szenario)
            befunde[aufgenommen.id] = pruefen(aufgenommen, graph)
        return befunde

    def _stelle(self, szenario_id: str) -> int:
        """Return a scenario's position, or raise KeyError."""
        for stelle, szenario in enumerate(self._szenarien):
            if szenario.id == szenario_id:
                return stelle
        raise KeyError(szenario_id)


def lesen(roh: object) -> Pooldatei:
    """Read an uploaded pool file, refusing anything this version cannot read."""
    try:
        return Pooldatei.model_validate(roh)
    except ValidationError as fehler:
        raise UngueltigeDatei(deutsch(fehler.errors())) from fehler
