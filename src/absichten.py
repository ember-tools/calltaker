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
from szenario import Szenario, pruefen
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


def befunde_von(szenario: Szenario, graph: Abfragegraph) -> list[dict]:
    """Return what the graph check finds for a scenario, as the views read it."""
    return [befund.nach_aussen() for befund in pruefen(szenario, graph)]


def pool_hinzufuegen(uebung: Uebung, absicht: Absicht, graph: Abfragegraph) -> dict:
    """Add a scenario to the pool."""
    try:
        szenario = uebung.pool.hinzufuegen(szenario_aus(absicht))
    except PoolVoll as fehler:
        raise AbsichtAbgelehnt(str(fehler), status=409) from fehler
    uebung.geaendert()
    return {"szenarioId": szenario.id, "befunde": befunde_von(szenario, graph)}


def pool_ersetzen(uebung: Uebung, absicht: Absicht, graph: Abfragegraph) -> dict:
    """Replace a scenario of the pool by its id."""
    szenario = szenario_aus(absicht)
    try:
        uebung.pool.ersetzen(szenario)
    except KeyError as fehler:
        raise AbsichtAbgelehnt(UNBEKANNTES_SZENARIO, status=404) from fehler
    uebung.geaendert()
    return {"szenarioId": szenario.id, "befunde": befunde_von(szenario, graph)}


def pool_entfernen(uebung: Uebung, absicht: Absicht, _: Abfragegraph) -> dict:
    """Remove a scenario from the pool."""
    try:
        uebung.pool.entfernen(absicht.szenario_id or "")
    except KeyError as fehler:
        raise AbsichtAbgelehnt(UNBEKANNTES_SZENARIO, status=404) from fehler
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
    uebung.geaendert()
    return {}


def pool_importieren(uebung: Uebung, absicht: Absicht, graph: Abfragegraph) -> dict:
    """Take the scenarios of an uploaded pool file, replacing or extending the pool."""
    try:
        befunde = uebung.pool.importieren(absicht.datei, absicht.modus, graph)
    except (UngueltigeDatei, PoolVoll) as fehler:
        raise AbsichtAbgelehnt(str(fehler), status=422) from fehler
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


def parameter_setzen(uebung: Uebung, absicht: Absicht, _: Abfragegraph) -> dict:
    """Change some of the queue's settings; those not given keep their values."""
    bisher = uebung.engine.parameter.model_dump(by_alias=True)
    try:
        parameter = Parameter.model_validate({**bisher, **(absicht.parameter or {})})
    except ValidationError as fehler:
        raise AbsichtAbgelehnt(deutsch(fehler.errors()), status=422) from fehler
    uebung.engine.parameter_setzen(parameter)
    return {}


ABSICHTEN: dict[str, tuple[set[Rolle], Ausfuehrung]] = {
    "pool.hinzufuegen": ({Rolle.AUSBILDER}, pool_hinzufuegen),
    "pool.ersetzen": ({Rolle.AUSBILDER}, pool_ersetzen),
    "pool.entfernen": ({Rolle.AUSBILDER}, pool_entfernen),
    "pool.verschieben": ({Rolle.AUSBILDER}, pool_verschieben),
    "pool.importieren": ({Rolle.AUSBILDER}, pool_importieren),
    "spiegeln": ({Rolle.TRAINEE}, spiegeln),
    "bereit": ({Rolle.TRAINEE}, bereit),
    "annehmen": ({Rolle.TRAINEE}, annehmen),
    "beenden": ({Rolle.TRAINEE}, beenden),
    "eintragen": ({Rolle.TRAINEE}, eintragen),
    "engine.pausieren": ({Rolle.AUSBILDER}, pausieren),
    "engine.sofort": ({Rolle.AUSBILDER}, sofort_klingeln),
    "engine.parameter": ({Rolle.AUSBILDER}, parameter_setzen),
    "anruf.auflegen": ({Rolle.AUSBILDER}, auflegen),
}
