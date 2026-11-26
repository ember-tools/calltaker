"""Exercises: one trainer, one trainee, a pool and the calls, held in memory and reached by code."""

import hashlib
import logging
import random
import secrets
import sqlite3
import time
from collections.abc import Callable
from typing import Any

from anruf import Anruf
from engine import Engine
from pool import Pool, befunde_nach_aussen
from rolle import Rolle
from szenario import Szenario
from szenariogenerator import Erzeugung, NichtsZuZiehen

Erzeuger = Callable[[Erzeugung], Szenario]

logger = logging.getLogger(__name__)

CODE_ZEICHEN = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LAENGE = 8
UNBESUCHT_FRIST = 600.0
ONLINE_FRIST = 8.0


def neuer_code(praefix: str) -> str:
    """Return a code that is hard to guess and easy to read out: a prefix and eight characters."""
    return praefix + "-" + "".join(secrets.choice(CODE_ZEICHEN) for _ in range(CODE_LAENGE))


class Uebung:
    """One exercise and everything that changes in it.

    Every change raises `version`, which is what lets a poll that finds nothing new end with an
    empty answer. A role counts as connected while its last poll is at most `ONLINE_FRIST` seconds
    old. Hidden browser tabs poll every five seconds, so the window must stay well above
    that, or a hidden role would flicker between connected and not connected.
    """

    def __init__(
        self,
        ausbilder_code: str,
        trainee_code: str,
        uhr: Callable[[], float],
        erzeuger: Erzeuger | None = None,
    ) -> None:
        """Start an exercise with an empty pool and no calls; `erzeuger` makes up scenarios."""
        self.ausbilder_code = ausbilder_code
        self.trainee_code = trainee_code
        self.uhr = uhr
        self.pool = Pool()
        self.anrufe: list[Anruf] = []
        self.spiegel: dict[str, Any] = {}
        self.version = 1
        self.letzte_abfrage: dict[Rolle, float] = {}
        self.verbunden: dict[Rolle, bool] = {Rolle.AUSBILDER: False, Rolle.TRAINEE: False}
        self.angelegt_um = uhr()
        self.erzeuger = erzeuger
        self.erzeugung = Erzeugung()
        self.engine = Engine(self, uhr, random.Random())

    @property
    def kennung(self) -> str:
        """Return a name for logs that grants no access: a short hash of the trainer code."""
        return hashlib.sha256(self.ausbilder_code.encode()).hexdigest()[:10]

    def pool_entnehmen(self) -> Szenario | None:
        """Take the first scenario of the pool for the next call.

        An empty pool makes one up when the engine is set to, and otherwise gives nothing, so no
        call rings until the trainer adds a scenario.
        """
        szenarien = self.pool.szenarien
        if szenarien:
            return self.pool.entfernen(szenarien[0].id)
        if not self.engine.parameter.auto_generieren:
            return None
        try:
            return self.erzeugen()
        except NichtsZuZiehen:
            return None
        except sqlite3.Error, OSError:
            logger.exception("Übung %s: Szenario ließ sich nicht generieren", self.kennung)
            return None

    def erzeugen(self) -> Szenario:
        """Make up a scenario with the trainer's settings, or raise NichtsZuZiehen."""
        if self.erzeuger is None:
            raise NichtsZuZiehen("Der Generator steht nicht bereit.")
        return self.erzeuger(self.erzeugung)

    def geaendert(self) -> None:
        """Mark that something changed, so the next poll of every view fetches the state."""
        self.version += 1

    def abgefragt(self, rolle: Rolle) -> None:
        """Record a poll as a sign of life of its role."""
        self.letzte_abfrage[rolle] = self.uhr()
        self.verbindungen_pruefen()

    def verbindungen_pruefen(self) -> None:
        """Update who counts as connected, raising the version when that changes."""
        jetzt = self.uhr()
        for rolle in Rolle:
            zuletzt = self.letzte_abfrage.get(rolle)
            verbunden = zuletzt is not None and jetzt - zuletzt <= ONLINE_FRIST
            if verbunden != self.verbunden[rolle]:
                self.verbunden[rolle] = verbunden
                self.geaendert()

    def verlassen(self, jetzt: float, frist: float) -> bool:
        """Tell whether nobody has polled for longer than the given seconds.

        An exercise nobody has ever polled counts as left after `UNBESUCHT_FRIST`, so exercises
        created and never opened cannot fill the registry for long.
        """
        if not self.letzte_abfrage:
            return jetzt - self.angelegt_um > min(frist, UNBESUCHT_FRIST)
        return jetzt - max(self.letzte_abfrage.values()) > frist

    def zustand(self, rolle: Rolle) -> dict[str, Any]:
        """Return the state as the given role may see it."""
        verbunden = {rolle_.value: wert for rolle_, wert in self.verbunden.items()}
        if rolle == Rolle.TRAINEE:
            return {
                "verbunden": verbunden,
                "engine": self.engine.zustand(rolle),
                "anrufe": [anruf.fuer_trainee() for anruf in self.anrufe],
            }
        return {
            "codes": {"ausbilder": self.ausbilder_code, "trainee": self.trainee_code},
            "verbunden": verbunden,
            "engine": self.engine.zustand(rolle),
            "pool": [szenario.nach_aussen() for szenario in self.pool.szenarien],
            "poolBefunde": befunde_nach_aussen(self.pool.befunde),
            "poolStand": self.pool.stand,
            "erzeugung": self.erzeugung.model_dump(by_alias=True),
            "anrufe": [anruf.fuer_ausbilder() for anruf in self.anrufe],
            "spiegel": self.spiegel,
        }


class Uebungen:
    """Every exercise of this process, reachable by either of its codes."""

    def __init__(
        self,
        uhr: Callable[[], float] = time.time,
        hoechstens: int = 500,
        frist: float = 43200,
        erzeuger: Erzeuger | None = None,
    ) -> None:
        """Start without exercises; `frist` is how long an exercise nobody polls is kept."""
        self.uhr = uhr
        self.erzeuger = erzeuger
        self.hoechstens = hoechstens
        self.frist = frist
        self._nach_code: dict[str, tuple[Uebung, Rolle]] = {}

    def anlegen(self) -> Uebung:
        """Make a new exercise with fresh codes, refusing once the limit is reached.

        Left exercises are dropped first, so only exercises in use can hold the limit.
        """
        if len(self.alle()) >= self.hoechstens:
            self.aufraeumen()
        if len(self.alle()) >= self.hoechstens:
            raise UebungenVoll
        uebung = Uebung(self._freier_code("A"), self._freier_code("T"), self.uhr, self.erzeuger)
        self._nach_code[uebung.ausbilder_code] = (uebung, Rolle.AUSBILDER)
        self._nach_code[uebung.trainee_code] = (uebung, Rolle.TRAINEE)
        return uebung

    def finden(self, code: str) -> tuple[Uebung, Rolle] | None:
        """Return the exercise and the role a code stands for, ignoring case."""
        return self._nach_code.get(code.strip().upper())

    def alle(self) -> list[Uebung]:
        """Return every exercise once."""
        return list({id(u): u for u, _ in self._nach_code.values()}.values())

    def aufraeumen(self) -> list[Uebung]:
        """Drop every exercise nobody polls any more, and return them."""
        jetzt = self.uhr()
        weg = [u for u in self.alle() if u.verlassen(jetzt, self.frist)]
        for uebung in weg:
            del self._nach_code[uebung.ausbilder_code]
            del self._nach_code[uebung.trainee_code]
        return weg

    def _freier_code(self, praefix: str) -> str:
        """Return a code no exercise uses yet."""
        while (code := neuer_code(praefix)) in self._nach_code:
            pass
        return code


class UebungenVoll(Exception):
    """The process holds as many exercises as it may."""
