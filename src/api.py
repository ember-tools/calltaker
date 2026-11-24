"""HTTP routes of the server."""

import json
from functools import lru_cache

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import Response

import anleitungen
import beschwerden
import gefahrstoffe
from abfrage import Abfragegraph, laden
from einstellungen import einstellungen
from pool import Pool, PoolVoll, UngueltigeDatei, befunde_nach_aussen
from szenario import Szenario, pruefen
from szenariogenerator import WOHNUNGSPROTOKOLLE

router = APIRouter(prefix="/api")


@router.get("/gesundheit")
async def gesundheit() -> dict[str, str]:
    """Report that the server is up."""
    return {"status": "ok"}


@router.get("/abfrage")
async def abfrage() -> Response:
    """Return the question graph with its code index, as the frontend loads it."""
    return Response(content=abfragebuendel(), media_type="application/json")


@router.get("/gefahrstoffe")
async def gefahrstoffliste() -> Response:
    """Return the hazardous goods by UN number with where the list comes from."""
    return Response(content=gefahrstoffbuendel(), media_type="application/json")


@router.post("/szenario/pruefen")
async def szenario_pruefen(szenario: Szenario) -> dict:
    """Check a scenario against the question graph and return it with what the check found."""
    befunde = pruefen(szenario, abfragegraph())
    return {
        "szenario": szenario.nach_aussen(),
        "befunde": [befund.nach_aussen() for befund in befunde],
    }


@router.post("/pool/pruefen")
async def pool_pruefen(datei: object = Body()) -> dict:
    """Read an uploaded pool file and return its scenarios with what the check found for each."""
    pool = Pool()
    try:
        befunde = pool.importieren(datei, "ersetzen", abfragegraph())
    except (UngueltigeDatei, PoolVoll) as fehler:
        raise HTTPException(status_code=422, detail=str(fehler)) from fehler
    return {
        "szenarien": [szenario.nach_aussen() for szenario in pool.szenarien],
        "befunde": befunde_nach_aussen(befunde),
    }


@lru_cache
def abfragegraph() -> Abfragegraph:
    """Load and check the question graph once per process."""
    return laden(einstellungen().abfrage_verzeichnis)


@lru_cache
def anleitungskatalog() -> list[anleitungen.Anleitung]:
    """Load and check the instructions to the caller once per process."""
    return anleitungen.laden(einstellungen().anleitungen_verzeichnis, abfragegraph())


@lru_cache
def beschwerdekatalog() -> list[beschwerden.Lage]:
    """Load and check the complaints callers describe once per process."""
    return beschwerden.laden(einstellungen().beschwerden_verzeichnis, abfragegraph())


@lru_cache
def gefahrstoffe_geladen() -> list[gefahrstoffe.Stoff]:
    """Load the hazardous goods once per process."""
    return gefahrstoffe.laden(einstellungen().gefahrstoffe_verzeichnis)


@lru_cache
def gefahrstoffbuendel() -> bytes:
    """Serialise the hazardous goods for the frontend once per process."""
    buendel = {
        "herkunft": gefahrstoffe.herkunft(einstellungen().gefahrstoffe_verzeichnis),
        "stoffe": [stoff.model_dump() for stoff in gefahrstoffe_geladen()],
    }
    return json.dumps(buendel, ensure_ascii=False, separators=(",", ":")).encode()


@lru_cache
def abfragebuendel() -> bytes:
    """Serialise the question graph and the instructions for the frontend once per process."""
    buendel = {
        **abfragegraph().buendel(),
        "anleitungen": anleitungen.nach_aussen(anleitungskatalog()),
        "wohnungsprotokolle": sorted(WOHNUNGSPROTOKOLLE),
    }
    return json.dumps(buendel, ensure_ascii=False, separators=(",", ":")).encode()
