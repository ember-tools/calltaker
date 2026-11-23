"""Calls: a scenario on its way through queue and conversation, and who may see what of it."""

from enum import StrEnum

from pydantic import Field

from szenario import Modell, Szenario, neue_id


class Anrufzustand(StrEnum):
    """Where a call stands."""

    WARTET = "wartet"
    GESPRAECH = "gespraech"
    BEENDET = "beendet"
    AUFGELEGT = "aufgelegt"


class Anruf(Modell):
    """One call: its scenario, its state, its times and what the trainee entered.

    Times are seconds of the server's clock (`time.time()`), which the views count from.
    """

    id: str = Field(default_factory=neue_id)
    szenario: Szenario
    zustand: Anrufzustand = Anrufzustand.WARTET
    klingelt_seit: float
    angenommen_um: float | None = None
    beendet_um: float | None = None
    eintraege: dict = Field(default_factory=dict)

    def fuer_ausbilder(self) -> dict:
        """Return the whole call, truth included."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)

    def fuer_trainee(self) -> dict:
        """Return what the trainee may see of the call in its current state.

        While a call waits or runs, the trainee sees the number shown and the times, plus its own
        entries; the scenario's truth only once the call has ended, for the debrief. A caller who
        hung up shows only the number and the wait.
        """
        anrufer = self.szenario.anrufer
        sicht = {
            "id": self.id,
            "zustand": self.zustand.value,
            "klingeltSeit": self.klingelt_seit,
            "rufnummer": None if anrufer.rufnummer_unterdrueckt else anrufer.rufnummer,
            "rufnummerUnterdrueckt": anrufer.rufnummer_unterdrueckt,
        }
        if self.angenommen_um is not None:
            sicht["angenommenUm"] = self.angenommen_um
        if self.beendet_um is not None:
            sicht["beendetUm"] = self.beendet_um
        if self.zustand in (Anrufzustand.GESPRAECH, Anrufzustand.BEENDET):
            sicht["eintraege"] = self.eintraege
        if self.zustand == Anrufzustand.BEENDET:
            sicht["szenario"] = self.szenario.nach_aussen()
        return {schluessel: wert for schluessel, wert in sicht.items() if wert is not None}
