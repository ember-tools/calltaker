"""The pool of scenarios an exercise draws its calls from, and its file format."""

from typing import Literal

from pydantic import Field, ValidationError

from abfrage import Abfragegraph
from fehlermeldung import deutsch
from szenario import Befund, Modell, Szenario, neue_id, pruefen

POOL_FORMAT = "calltaker-pool"
POOL_VERSION = 1
POOL_HOECHSTENS = 200


class Pooldatei(Modell):
    """A downloaded pool, as it is uploaded again."""

    format: Literal["calltaker-pool"]
    version: Literal[1]
    abfrage_version: int
    szenarien: list[Szenario] = Field(default_factory=list)


class PoolVoll(ValueError):
    """A pool that already holds as many scenarios as it may."""

    def __init__(self) -> None:
        """Say so in German."""
        super().__init__(f"Ein Pool hält höchstens {POOL_HOECHSTENS} Szenarien.")


class UngueltigeDatei(ValueError):
    """An uploaded file that is not a pool this version can read."""


class Pool:
    """The scenarios of one exercise, in the trainer's order, with what the graph check found.

    The findings are kept per scenario when it is added, replaced or imported, so the trainer's
    list can mark scenarios to correct without checking the whole pool on every poll. The graph
    only changes with a restart, which also empties the pool, so they stay current. They outlive
    a scenario the engine draws for a call, so it keeps its marks when it comes back; only the
    trainer's removal or a replacing import forgets them.

    `stand` counts the trainer's changes to the pool, not the engine's drawing and returning, so
    the trainer can be reminded to download only what they changed.
    """

    def __init__(self) -> None:
        """Start with an empty pool."""
        self._szenarien: list[Szenario] = []
        self._befunde: dict[str, list[Befund]] = {}
        self.stand = 0

    @property
    def szenarien(self) -> list[Szenario]:
        """Return the scenarios in order."""
        return list(self._szenarien)

    def hinzufuegen(self, szenario: Szenario) -> Szenario:
        """Append a scenario; an id already in the pool gets a new one."""
        if len(self._szenarien) >= POOL_HOECHSTENS:
            raise PoolVoll
        if self.finden(szenario.id) is not None:
            szenario = szenario.model_copy(update={"id": neue_id()})
        self._szenarien.append(szenario)
        return szenario

    def ersetzen(self, szenario: Szenario) -> None:
        """Replace the scenario with the same id."""
        self._szenarien[self._stelle(szenario.id)] = szenario

    def entfernen(self, szenario_id: str) -> Szenario:
        """Remove a scenario and return it, keeping its findings should it come back."""
        return self._szenarien.pop(self._stelle(szenario_id))

    def vergessen(self, szenario_id: str) -> None:
        """Forget the findings of a scenario the trainer removed."""
        self._befunde.pop(szenario_id, None)

    def vermerken(self, szenario: Szenario, graph: Abfragegraph) -> list[Befund]:
        """Check a scenario of the pool against the graph, keep and return what was found."""
        befunde = pruefen(szenario, graph)
        if befunde:
            self._befunde[szenario.id] = befunde
        else:
            self._befunde.pop(szenario.id, None)
        return befunde

    @property
    def befunde(self) -> dict[str, list[Befund]]:
        """Return the findings of the scenarios in the pool that have any, by scenario id."""
        da = {szenario.id for szenario in self._szenarien}
        return {
            szenario_id: liste for szenario_id, liste in self._befunde.items() if szenario_id in da
        }

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
        bestand = 0 if modus == "ersetzen" else len(self._szenarien)
        if bestand + len(datei.szenarien) > POOL_HOECHSTENS:
            raise PoolVoll
        if modus == "ersetzen":
            self._szenarien = []
            self._befunde = {}
        befunde = {}
        for szenario in datei.szenarien:
            aufgenommen = self.hinzufuegen(szenario)
            befunde[aufgenommen.id] = self.vermerken(aufgenommen, graph)
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


def befunde_nach_aussen(befunde: dict[str, list[Befund]]) -> dict[str, list[dict]]:
    """Return the findings per scenario as the views read them."""
    return {szenario_id: [b.nach_aussen() for b in liste] for szenario_id, liste in befunde.items()}
