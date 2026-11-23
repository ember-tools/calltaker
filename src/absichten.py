"""What the views ask an exercise to do, checked against the asking role and carried out."""

from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel

from abfrage import Abfragegraph
from eintraege import Eintraege, uebernehmen
from engine import Parameter
from fehlermeldung import deutsch
from pool import PoolVoll, UngueltigeDatei, befunde_nach_aussen
from rolle import Rolle
from szenario import Szenario
from szenariogenerator import Erzeugung, NichtsZuZiehen
from uebung import Uebung

SPIEGEL_HOECHSTENS = 4096
UNBEKANNTES_SZENARIO = "Dieses Szenario gibt es nicht."


class AbsichtAbgelehnt(Exception):
    """An intent the exercise refuses, with the reason in German."""

    def __init__(self, grund: str, status: int = 400) -> None:
        """Carry the reason and the HTTP status to answer with."""
        super().__init__(grund)
        self.status = status


class Absicht(BaseModel):
    """One intent: what is wanted, and the data it needs."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    art: str
    szenario: dict[str, Any] | None = None
    szenario_id: str | None = None
    ziel: int | None = None
    datei: Any = None
    modus: Literal["ersetzen", "anhaengen"] = "anhaengen"
    felder: dict[str, Any] = Field(default_factory=dict)
    anruf_id: str | None = None
    eintraege: dict[str, Any] | None = None
    an: bool | None = None
    parameter: dict[str, Any] | None = None
    anzahl: int | None = None
    erzeugung: dict[str, Any] | None = None
    anleitung: str | None = Field(None, max_length=200)
    gegeben: bool | None = None


Ausfuehrung = Callable[[Uebung, Absicht, Abfragegraph], dict[str, Any]]


def ausfuehren(uebung: Uebung, rolle: Rolle, absicht: Absicht, graph: Abfragegraph) -> dict:
    """Carry out an intent for a role and return its result; refuse what the role may not do.

    Each intent raises the exercise's version itself when it changed something, so a refused one,
    or a mirror that did not change, leaves the views' state as it was.
    """
    eintrag = ABSICHTEN.get(absicht.art)
    if eintrag is None:
        raise AbsichtAbgelehnt(f"Die Absicht {absicht.art} gibt es nicht.")
    erlaubt, ausfuehrung = eintrag
    if rolle not in erlaubt:
        raise AbsichtAbgelehnt("Das darf diese Rolle nicht.", status=403)
    return ausfuehrung(uebung, absicht, graph)


def szenario_aus(absicht: Absicht) -> Szenario:
    """Read the scenario an intent carries, refusing an invalid one in German."""
    if absicht.szenario is None:
        raise AbsichtAbgelehnt("Das Szenario fehlt.")
    try:
        return Szenario.model_validate(absicht.szenario)
    except ValidationError as fehler:
        raise AbsichtAbgelehnt(deutsch(fehler.errors()), status=422) from fehler


def befunde_von(uebung: Uebung, szenario: Szenario, graph: Abfragegraph) -> list[dict]:
    """Check a scenario of the pool, keep the findings and return them as the views read them."""
    return [befund.nach_aussen() for befund in uebung.pool.vermerken(szenario, graph)]


def pool_hinzufuegen(uebung: Uebung, absicht: Absicht, graph: Abfragegraph) -> dict:
    """Add a scenario to the pool."""
    try:
        szenario = uebung.pool.hinzufuegen(szenario_aus(absicht))
    except PoolVoll as fehler:
        raise AbsichtAbgelehnt(str(fehler), status=409) from fehler
    befunde = befunde_von(uebung, szenario, graph)
    uebung.pool.stand += 1
    uebung.geaendert()
    return {"szenarioId": szenario.id, "befunde": befunde}


def pool_ersetzen(uebung: Uebung, absicht: Absicht, graph: Abfragegraph) -> dict:
    """Replace a scenario of the pool by its id."""
    szenario = szenario_aus(absicht)
    try:
        uebung.pool.ersetzen(szenario)
    except KeyError as fehler:
        raise AbsichtAbgelehnt(UNBEKANNTES_SZENARIO, status=404) from fehler
    befunde = befunde_von(uebung, szenario, graph)
    uebung.pool.stand += 1
    uebung.geaendert()
    return {"szenarioId": szenario.id, "befunde": befunde}


def pool_entfernen(uebung: Uebung, absicht: Absicht, _: Abfragegraph) -> dict:
    """Remove a scenario from the pool."""
    try:
        uebung.pool.entfernen(absicht.szenario_id or "")
    except KeyError as fehler:
        raise AbsichtAbgelehnt(UNBEKANNTES_SZENARIO, status=404) from fehler
    uebung.pool.vergessen(absicht.szenario_id or "")
    uebung.pool.stand += 1
    uebung.geaendert()
    return {}


def pool_verschieben(uebung: Uebung, absicht: Absicht, _: Abfragegraph) -> dict:
    """Move a scenario of the pool to another position."""
    if absicht.ziel is None:
        raise AbsichtAbgelehnt("Das Ziel der Verschiebung fehlt.")
    try:
        uebung.pool.verschieben(absicht.szenario_id or "", absicht.ziel)
    except KeyError as fehler:
        raise AbsichtAbgelehnt(UNBEKANNTES_SZENARIO, status=404) from fehler
    uebung.pool.stand += 1
    uebung.geaendert()
    return {}


def pool_importieren(uebung: Uebung, absicht: Absicht, graph: Abfragegraph) -> dict:
    """Take the scenarios of an uploaded pool file, replacing or extending the pool."""
    try:
        befunde = uebung.pool.importieren(absicht.datei, absicht.modus, graph)
    except (UngueltigeDatei, PoolVoll) as fehler:
        raise AbsichtAbgelehnt(str(fehler), status=422) from fehler
    uebung.pool.stand += 1
    uebung.geaendert()
    return {"befunde": befunde_nach_aussen(befunde)}


def spiegeln(uebung: Uebung, absicht: Absicht, _: Abfragegraph) -> dict:
    """Mirror what the trainee is typing, for the trainer to watch."""
    if len(str(absicht.felder)) > SPIEGEL_HOECHSTENS:
        raise AbsichtAbgelehnt("Zu viel auf einmal gespiegelt.", status=413)
    if absicht.felder != uebung.spiegel:
        uebung.spiegel = absicht.felder
        uebung.geaendert()
    return {}


def bereit(uebung: Uebung, _: Absicht, __: Abfragegraph) -> dict:
    """Start the queue: the trainee is ready for calls."""
    uebung.engine.starten()
    return {}


def annehmen(uebung: Uebung, absicht: Absicht, _: Abfragegraph) -> dict:
    """Take the longest waiting call."""
    try:
        anruf = uebung.engine.annehmen(absicht.anruf_id or "")
    except ValueError as fehler:
        raise AbsichtAbgelehnt(str(fehler), status=409) from fehler
    return {"anrufId": anruf.id}


def beenden(uebung: Uebung, _: Absicht, __: Abfragegraph) -> dict:
    """End the running conversation."""
    try:
        anruf = uebung.engine.beenden()
    except ValueError as fehler:
        raise AbsichtAbgelehnt(str(fehler), status=409) from fehler
    return {"anrufId": anruf.id}


def eintragen(uebung: Uebung, absicht: Absicht, _: Abfragegraph) -> dict:
    """Take the trainee's entries for the running conversation."""
    anruf = uebung.engine.im_gespraech()
    if anruf is None:
        raise AbsichtAbgelehnt("Es läuft kein Gespräch.", status=409)
    if absicht.anruf_id is not None and absicht.anruf_id != anruf.id:
        raise AbsichtAbgelehnt("Dieses Gespräch läuft nicht mehr.", status=409)
    if absicht.eintraege is None:
        raise AbsichtAbgelehnt("Die Einträge fehlen.", status=422)
    try:
        neu = Eintraege.model_validate(absicht.eintraege)
    except ValidationError as fehler:
        raise AbsichtAbgelehnt(deutsch(fehler.errors()), status=422) from fehler
    uebernommen = uebernehmen(anruf.eintraege, neu, uebung.uhr())
    if uebernommen != anruf.eintraege:
        anruf.eintraege = uebernommen
        uebung.geaendert()
    return {"zeiten": uebernommen.zeiten.model_dump(by_alias=True)}


def pausieren(uebung: Uebung, absicht: Absicht, _: Abfragegraph) -> dict:
    """Pause or resume the queue by hand."""
    if absicht.an is None:
        raise AbsichtAbgelehnt("Ob pausiert werden soll, fehlt.")
    uebung.engine.pausieren(absicht.an)
    return {}


def sofort_klingeln(uebung: Uebung, absicht: Absicht, _: Abfragegraph) -> dict:
    """Ring a scenario of the pool at once."""
    try:
        anruf = uebung.engine.sofort_klingeln(absicht.szenario_id or "")
    except KeyError as fehler:
        raise AbsichtAbgelehnt(UNBEKANNTES_SZENARIO, status=404) from fehler
    except ValueError as fehler:
        raise AbsichtAbgelehnt(str(fehler), status=409) from fehler
    return {"anrufId": anruf.id}


def auflegen(uebung: Uebung, absicht: Absicht, _: Abfragegraph) -> dict:
    """Let a waiting caller hang up."""
    try:
        uebung.engine.auflegen(absicht.anruf_id or "")
    except KeyError as fehler:
        raise AbsichtAbgelehnt("Dieser Anruf wartet nicht.", status=404) from fehler
    return {}


KORREKTUREN_HOECHSTENS = 100


def anleitung_korrigieren(uebung: Uebung, absicht: Absicht, _: Abfragegraph) -> dict:
    """Let the trainer count an instruction as given or not, whatever the trainee ticked."""
    anruf = next((a for a in uebung.anrufe if a.id == absicht.anruf_id), None)
    if anruf is None:
        raise AbsichtAbgelehnt("Diesen Anruf gibt es nicht.", status=404)
    if not absicht.anleitung or absicht.gegeben is None:
        raise AbsichtAbgelehnt("Welche Anleitung und ob sie gegeben wurde, fehlt.", status=422)
    if absicht.anleitung not in anruf.korrektur and len(anruf.korrektur) >= KORREKTUREN_HOECHSTENS:
        raise AbsichtAbgelehnt("Zu viele Korrekturen für diesen Anruf.", status=422)
    anruf.korrektur[absicht.anleitung] = absicht.gegeben
    uebung.geaendert()
    return {}


def parameter_setzen(uebung: Uebung, absicht: Absicht, _: Abfragegraph) -> dict:
    """Change some of the queue's settings; those not given keep their values."""
    bisher = uebung.engine.parameter.model_dump(by_alias=True)
    try:
        parameter = Parameter.model_validate({**bisher, **(absicht.parameter or {})})
    except ValidationError as fehler:
        raise AbsichtAbgelehnt(deutsch(fehler.errors()), status=422) from fehler
    uebung.engine.parameter_setzen(parameter)
    return {}


GENERIEREN_HOECHSTENS = 20


def pool_generieren(uebung: Uebung, absicht: Absicht, graph: Abfragegraph) -> dict:
    """Make up scenarios with the trainer's settings and add them to the pool."""
    anzahl = 1 if absicht.anzahl is None else absicht.anzahl
    if not 1 <= anzahl <= GENERIEREN_HOECHSTENS:
        raise AbsichtAbgelehnt(
            f"Es lassen sich 1 bis {GENERIEREN_HOECHSTENS} auf einmal generieren."
        )
    ids = []
    try:
        for _ in range(anzahl):
            szenario = uebung.pool.hinzufuegen(uebung.erzeugen())
            befunde_von(uebung, szenario, graph)
            ids.append(szenario.id)
    except NichtsZuZiehen as fehler:
        raise AbsichtAbgelehnt(str(fehler), status=409) from fehler
    except PoolVoll as fehler:
        raise AbsichtAbgelehnt(str(fehler), status=409) from fehler
    finally:
        if ids:
            uebung.pool.stand += 1
            uebung.geaendert()
    return {"szenarioIds": ids}


def erzeugung_einstellen(uebung: Uebung, absicht: Absicht, _: Abfragegraph) -> dict:
    """Change the settings for made-up scenarios; those not given keep their values."""
    bisher = uebung.erzeugung.model_dump(by_alias=True)
    try:
        uebung.erzeugung = Erzeugung.model_validate({**bisher, **(absicht.erzeugung or {})})
    except ValidationError as fehler:
        raise AbsichtAbgelehnt(deutsch(fehler.errors()), status=422) from fehler
    uebung.geaendert()
    return {}


ABSICHTEN: dict[str, tuple[set[Rolle], Ausfuehrung]] = {
    "pool.hinzufuegen": ({Rolle.AUSBILDER}, pool_hinzufuegen),
    "pool.ersetzen": ({Rolle.AUSBILDER}, pool_ersetzen),
    "pool.entfernen": ({Rolle.AUSBILDER}, pool_entfernen),
    "pool.verschieben": ({Rolle.AUSBILDER}, pool_verschieben),
    "pool.importieren": ({Rolle.AUSBILDER}, pool_importieren),
    "pool.generieren": ({Rolle.AUSBILDER}, pool_generieren),
    "erzeugung.einstellen": ({Rolle.AUSBILDER}, erzeugung_einstellen),
    "spiegeln": ({Rolle.TRAINEE}, spiegeln),
    "bereit": ({Rolle.TRAINEE}, bereit),
    "annehmen": ({Rolle.TRAINEE}, annehmen),
    "beenden": ({Rolle.TRAINEE}, beenden),
    "eintragen": ({Rolle.TRAINEE}, eintragen),
    "engine.pausieren": ({Rolle.AUSBILDER}, pausieren),
    "engine.sofort": ({Rolle.AUSBILDER}, sofort_klingeln),
    "engine.parameter": ({Rolle.AUSBILDER}, parameter_setzen),
    "anruf.auflegen": ({Rolle.AUSBILDER}, auflegen),
    "anleitung.korrigieren": ({Rolle.AUSBILDER}, anleitung_korrigieren),
}
