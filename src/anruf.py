"""Calls: a scenario on its way through queue and conversation, and who may see what of it."""

import random
from enum import StrEnum

from pydantic import Field, computed_field

from eintraege import Eintraege
from szenario import Modell, Szenario, neue_id

ANFAHRT = (60.0, 180.0)


class Anrufzustand(StrEnum):
    """Where a call stands."""

    WARTET = "wartet"
    GESPRAECH = "gespraech"
    BEENDET = "beendet"
    AUFGELEGT = "aufgelegt"


class Anruf(Modell):
    """One call: its scenario, its state, its times and what the trainee entered.

    Times are seconds of the server's clock (`time.time()`), which the views count from.
    `korrektur` holds the trainer's corrections of which instructions to the caller were given,
    kept apart from the trainee's entries so the trainee's next save does not undo them. During CPR
    the trainee stays on the line until the crews arrive, `ANFAHRT` seconds after the handover
    or, failing that, the start of CPR, unless the trainer lets them arrive earlier.
    """

    id: str = Field(default_factory=neue_id)
    szenario: Szenario
    zustand: Anrufzustand = Anrufzustand.WARTET
    klingelt_seit: float
    angenommen_um: float | None = None
    beendet_um: float | None = None
    eintraege: Eintraege = Field(default_factory=Eintraege)
    korrektur: dict[str, bool] = Field(default_factory=dict)
    anfahrt: float | None = None
    eingetroffen_um: float | None = None

    @computed_field
    @property
    def eintreffen_um(self) -> float | None:
        """Return when the crews reach a cardiac arrest, if CPR guidance has started.

        The trainer's word counts first; otherwise the drawn drive time after the handover, or
        after the start of CPR while the call is not handed over yet. Crews that arrived before
        a late handover stay arrived.
        """
        if self.eingetroffen_um is not None:
            return self.eingetroffen_um
        zeiten = self.eintraege.zeiten
        if self.anfahrt is None or zeiten.reanimation is None:
            return None
        ab_reanimation = zeiten.reanimation + self.anfahrt
        if zeiten.uebergabe is None or ab_reanimation <= zeiten.uebergabe:
            return ab_reanimation
        return zeiten.uebergabe + self.anfahrt

    def anfahrt_ziehen(self, zufall: random.Random) -> None:
        """Draw the crews' drive time once CPR guidance has started."""
        if self.anfahrt is None and self.eintraege.zeiten.reanimation is not None:
            self.anfahrt = zufall.uniform(*ANFAHRT)

    def fuer_ausbilder(self) -> dict:
        """Return the whole call, truth included."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)

    def fuer_trainee(self) -> dict:
        """Return what the trainee may see of the call in its current state.

        While a call waits or runs, the trainee sees the number shown and the times, plus its own
        entries; the scenario's truth and the trainer's corrections only once the call has ended,
        for the debrief. A caller who hung up shows only the number and the wait.
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
            sicht["eintraege"] = self.eintraege.nach_aussen()
            if self.eintreffen_um is not None:
                sicht["eintreffenUm"] = self.eintreffen_um
            if anrufer.funkzelle is not None:
                sicht["funkzelle"] = anrufer.funkzelle.model_dump(by_alias=True)
        if self.zustand == Anrufzustand.BEENDET:
            sicht["szenario"] = self.szenario.nach_aussen()
            sicht["korrektur"] = self.korrektur
        return {schluessel: wert for schluessel, wert in sicht.items() if wert is not None}
