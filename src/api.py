"""HTTP routes of the server."""

import json
from functools import lru_cache

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import Response

from abfrage import Abfragegraph, laden
from einstellungen import einstellungen
from pool import Pool, PoolVoll, UngueltigeDatei, befunde_nach_aussen
from szenario import Szenario, pruefen

router = APIRouter(prefix="/api")


@router.get("/gesundheit")
async def gesundheit() -> dict[str, str]:
    """Report that the server is up."""
    return {"status": "ok"}


@router.get("/abfrage")
async def abfrage() -> Response:
    """Return the question graph with its code index, as the frontend loads it."""
    return Response(content=abfragebuendel(), media_type="application/json")


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
def abfragebuendel() -> bytes:
    """Serialise the question graph for the frontend once per process."""
    return json.dumps(abfragegraph().buendel(), ensure_ascii=False, separators=(",", ":")).encode()
