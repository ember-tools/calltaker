"""The queue engine: when calls ring, when waiting callers give up, and when it all stands still.

The engine runs in the backend so both views see the same queue and the same times. It is driven
by `takt()`, which the server calls once a second, by the intents, which change the queue directly,
and by a clock passed in, so tests can run hours of queue in a moment. The clock is the wall clock
the views count from, since they show waits from the same absolute timestamps.

While nobody talks, the next call rings 5 to 10 seconds after the queue ran empty. While the
trainee is on a call, the gap to the next call is drawn from an exponential distribution whose
mean is `basis_abstand * abstand_faktor ** n` for n waiting calls: the more wait, the slower new
ones come. Every waiting caller draws a patience when the call rings, lognormal so that 90 % of
callers fall between `geduld_min` and `geduld_max`, and hangs up once it is spent. The exponential
gap has no memory, so whenever n changes the next ringing is simply drawn anew.

While the engine is paused, by hand or because a view has not polled for 10 seconds, nothing
rings and nobody hangs up, and the waits stand still: the queue's own time stays at the moment the
pause began, and on resuming every waiting call's ring time, its patience and the next ringing
move on by the length of the pause. A call that leaves the queue during a pause has its ring time
moved on by the part of the pause it spent waiting, so its wait counts only queue time.
"""

import contextlib
import math
import random
from collections.abc import Callable
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from anruf import Anruf, Anrufzustand
from pool import PoolVoll
from rolle import Rolle
from szenario import Szenario

if TYPE_CHECKING:
    from uebung import Uebung

AUTOMATISCHE_PAUSE_NACH = 10.0
ANRUFE_HOECHSTENS = 300
Z_95 = 1.6449


class Parameter(BaseModel):
    """The engine's settings, which the trainer may change while the exercise runs.

    Besides the queue, they hold the target times the debrief measures against: from answering to
    starting CPR guidance, and to handing a fire or rescue call over to dispatch.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    erstes_klingeln_min: float = Field(5, ge=0, le=600)
    erstes_klingeln_max: float = Field(10, ge=0, le=600)
    basis_abstand: float = Field(45, gt=0, le=3600)
    abstand_faktor: float = Field(1.6, ge=1, le=10)
    max_schlange: int = Field(5, ge=1, le=20)
    geduld_min: float = Field(60, gt=0, le=7200)
    geduld_max: float = Field(300, gt=0, le=7200)
    zurueck_in_pool: bool = True
    auto_generieren: bool = True
    ziel_reanimation: float = Field(120, ge=10, le=900)
    ziel_uebergabe: float = Field(60, ge=10, le=900)

    @model_validator(mode="after")
    def spannen(self) -> Self:
        """Require every span to run from its lower to its upper bound."""
        if self.erstes_klingeln_min > self.erstes_klingeln_max:
            raise ValueError("Das erste Klingeln braucht min ≤ max.")
        if self.geduld_min > self.geduld_max:
            raise ValueError("Die Geduld braucht min ≤ max.")
        return self


class Engine:
    """The queue of one exercise."""

    def __init__(self, uebung: Uebung, uhr: Callable[[], float], zufall: random.Random) -> None:
        """Attach an engine to an exercise; it starts when the trainee is ready."""
        self.uebung = uebung
        self.uhr = uhr
        self.zufall = zufall
        self.parameter = Parameter()
        self.gestartet = False
        self.manuell_pausiert = False
        self.automatisch_pausiert = False
        self.pausiert_seit: float | None = None
        self.naechstes_klingeln: float | None = None
        self.geduld_bis: dict[str, float] = {}

    @property
    def pausiert(self) -> bool:
        """Return whether the queue stands still."""
        return self.manuell_pausiert or self.automatisch_pausiert

    def queue_zeit(self) -> float:
        """Return the queue's own time: the present, or the moment the pause began."""
        return self.pausiert_seit if self.pausiert_seit is not None else self.uhr()

    def wartende(self) -> list[Anruf]:
        """Return the waiting calls, longest waiting first."""
        return [a for a in self.uebung.anrufe if a.zustand == Anrufzustand.WARTET]

    def im_gespraech(self) -> Anruf | None:
        """Return the call the trainee is talking on, if any."""
        return next((a for a in self.uebung.anrufe if a.zustand == Anrufzustand.GESPRAECH), None)

    def starten(self) -> None:
        """Start the queue once the trainee is ready."""
        if self.gestartet:
            return
        self.gestartet = True
        self._neu_planen()
        self.uebung.geaendert()

    def takt(self) -> None:
        """Move the queue on to the present: pause or resume, hang up, ring."""
        jetzt = self.uhr()
        self._automatische_pause(jetzt)
        if not self.gestartet or self.pausiert:
            return
        self._auflegen_lassen(jetzt)
        if self.naechstes_klingeln is not None and jetzt >= self.naechstes_klingeln:
            self.naechstes_klingeln = None
            try:
                if len(self.wartende()) < self.parameter.max_schlange:
                    self._klingeln(self.uebung.pool_entnehmen())
            finally:
                self._neu_planen()
                self.uebung.geaendert()

    def annehmen(self, anruf_id: str) -> Anruf:
        """Take the longest waiting call; refuse any other, or a second conversation."""
        if self.im_gespraech() is not None:
            raise ValueError("Es läuft schon ein Gespräch.")
        wartende = self.wartende()
        if not wartende or wartende[0].id != anruf_id:
            raise ValueError("Angenommen wird der am längsten wartende Anruf.")
        anruf = wartende[0]
        self._wartezeit_abschliessen(anruf)
        anruf.zustand = Anrufzustand.GESPRAECH
        anruf.angenommen_um = self.uhr()
        self.geduld_bis.pop(anruf.id, None)
        self._neu_planen()
        self.uebung.geaendert()
        return anruf

    def beenden(self) -> Anruf:
        """End the running conversation."""
        anruf = self.im_gespraech()
        if anruf is None:
            raise ValueError("Es läuft kein Gespräch.")
        anruf.zustand = Anrufzustand.BEENDET
        anruf.beendet_um = self.uhr()
        self._neu_planen()
        self.uebung.geaendert()
        return anruf

    def sofort_klingeln(self, szenario_id: str) -> Anruf:
        """Ring a scenario of the pool at once, never beyond the queue's limit."""
        if len(self.wartende()) >= self.parameter.max_schlange:
            raise ValueError("Die Warteschlange ist voll.")
        szenario = self.uebung.pool.finden(szenario_id)
        if szenario is None:
            raise KeyError(szenario_id)
        self.uebung.pool.entfernen(szenario_id)
        anruf = self._klingeln(szenario)
        self._neu_planen()
        return anruf

    def auflegen(self, anruf_id: str) -> Anruf:
        """Let a waiting caller hang up now."""
        anruf = next((a for a in self.wartende() if a.id == anruf_id), None)
        if anruf is None:
            raise KeyError(anruf_id)
        self._aufgelegt(anruf, self.uhr())
        self._neu_planen()
        return anruf

    def pausieren(self, an: bool) -> None:
        """Pause or resume the queue by hand."""
        if an == self.manuell_pausiert:
            return
        vorher = self.pausiert
        self.manuell_pausiert = an
        self.uebung.geaendert()
        self._pause_wechseln(vorher, self.uhr())

    def _wartezeit_abschliessen(self, anruf: Anruf) -> None:
        """Move a call's ring time on by the part of a running pause, as it leaves the queue."""
        if self.pausiert_seit is not None:
            anruf.klingelt_seit += self.uhr() - self.pausiert_seit

    def parameter_setzen(self, parameter: Parameter) -> None:
        """Change the settings and draw the next ringing under them."""
        self.parameter = parameter
        if self.gestartet:
            self._neu_planen()
        self.uebung.geaendert()

    def zustand(self, rolle: Rolle) -> dict:
        """Return the engine's state as the given role may see it."""
        sicht = {
            "gestartet": self.gestartet,
            "pausiert": self.pausiert,
            "automatischPausiert": self.automatisch_pausiert,
            "ziele": {
                "reanimation": self.parameter.ziel_reanimation,
                "uebergabe": self.parameter.ziel_uebergabe,
            },
        }
        if rolle == Rolle.AUSBILDER:
            sicht["manuellPausiert"] = self.manuell_pausiert
            sicht["naechstesKlingeln"] = self._naechstes_in_echtzeit()
            sicht["parameter"] = self.parameter.model_dump(by_alias=True)
        if self.pausiert_seit is not None:
            sicht["pausiertSeit"] = self.pausiert_seit
        return sicht

    def _naechstes_in_echtzeit(self) -> float | None:
        """Return the next ringing as wall-clock time, as if the queue resumed right now."""
        if self.naechstes_klingeln is None or self.pausiert_seit is None:
            return self.naechstes_klingeln
        return self.naechstes_klingeln + self.uhr() - self.pausiert_seit

    def _automatische_pause(self, jetzt: float) -> None:
        """Pause while a role has not polled for too long, and resume once both are back."""
        fehlt = any(
            jetzt - self.uebung.letzte_abfrage.get(rolle, -math.inf) > AUTOMATISCHE_PAUSE_NACH
            for rolle in Rolle
        )
        if fehlt == self.automatisch_pausiert:
            return
        vorher = self.pausiert
        self.automatisch_pausiert = fehlt
        self.uebung.geaendert()
        self._pause_wechseln(vorher, jetzt)

    def _pause_wechseln(self, vorher: bool, jetzt: float) -> None:
        """Freeze the waits when the queue stops, and shift them on by the pause when it goes on."""
        if self.pausiert == vorher:
            return
        if self.pausiert:
            self.pausiert_seit = jetzt
        elif self.pausiert_seit is not None:
            dauer = jetzt - self.pausiert_seit
            self.pausiert_seit = None
            for anruf in self.wartende():
                anruf.klingelt_seit += dauer
                self.geduld_bis[anruf.id] += dauer
            if self.naechstes_klingeln is not None:
                self.naechstes_klingeln += dauer
        self.uebung.geaendert()

    def _auflegen_lassen(self, jetzt: float) -> None:
        """Let every caller whose patience is spent hang up."""
        aufgelegt = [a for a in self.wartende() if jetzt >= self.geduld_bis.get(a.id, math.inf)]
        for anruf in aufgelegt:
            self._aufgelegt(anruf, jetzt)
        if aufgelegt:
            self._neu_planen()

    def _aufgelegt(self, anruf: Anruf, jetzt: float) -> None:
        """Mark a waiting call as hung up; its scenario goes back to the pool if wanted and room."""
        self._wartezeit_abschliessen(anruf)
        anruf.zustand = Anrufzustand.AUFGELEGT
        anruf.beendet_um = jetzt
        self.geduld_bis.pop(anruf.id, None)
        self.uebung.geaendert()
        if self.parameter.zurueck_in_pool:
            with contextlib.suppress(PoolVoll):
                self.uebung.pool.hinzufuegen(anruf.szenario)

    def _klingeln(self, szenario: Szenario | None) -> Anruf | None:
        """Put a scenario into the queue as a ringing call, with the patience its caller has."""
        if szenario is None:
            return None
        jetzt = self.queue_zeit()
        anruf = Anruf(szenario=szenario, klingelt_seit=jetzt)
        self.uebung.anrufe.append(anruf)
        self._alte_anrufe_kuerzen()
        self.geduld_bis[anruf.id] = jetzt + self._geduld()
        self.uebung.geaendert()
        return anruf

    def _alte_anrufe_kuerzen(self) -> None:
        """Keep at most `ANRUFE_HOECHSTENS` calls, dropping the oldest finished ones first."""
        ueberzaehlig = len(self.uebung.anrufe) - ANRUFE_HOECHSTENS
        if ueberzaehlig <= 0:
            return
        fertig = [
            a
            for a in self.uebung.anrufe
            if a.zustand in (Anrufzustand.BEENDET, Anrufzustand.AUFGELEGT)
        ]
        weg = {id(a) for a in fertig[:ueberzaehlig]}
        self.uebung.anrufe[:] = [a for a in self.uebung.anrufe if id(a) not in weg]

    def _neu_planen(self) -> None:
        """Draw when the next call rings, from the queue as it stands, in the queue's own time."""
        jetzt = self.queue_zeit()
        n = len(self.wartende())
        if self.im_gespraech() is None and n == 0:
            p = self.parameter
            self.naechstes_klingeln = jetzt + self.zufall.uniform(
                p.erstes_klingeln_min, p.erstes_klingeln_max
            )
        else:
            mittel = self.parameter.basis_abstand * self.parameter.abstand_faktor**n
            self.naechstes_klingeln = jetzt + self.zufall.expovariate(1 / mittel)

    def _geduld(self) -> float:
        """Draw a caller's patience: lognormal, 90 % of draws between the two bounds."""
        unten = math.log(self.parameter.geduld_min)
        oben = math.log(self.parameter.geduld_max)
        return self.zufall.lognormvariate(
            (unten + oben) / 2, max((oben - unten) / (2 * Z_95), 1e-9)
        )
