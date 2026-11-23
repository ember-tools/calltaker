"""HTTP routes of the server."""

import json
from functools import lru_cache

from fastapi import APIRouter
from fastapi.responses import Response

from abfrage import laden
from einstellungen import einstellungen

router = APIRouter(prefix="/api")


@router.get("/gesundheit")
async def gesundheit() -> dict[str, str]:
    """Report that the server is up."""
    return {"status": "ok"}


@router.get("/abfrage")
async def abfrage() -> Response:
    """Return the question graph with its code index, as the frontend loads it."""
    return Response(content=abfragebuendel(), media_type="application/json")


@lru_cache
def abfragebuendel() -> bytes:
    """Load, check and serialise the question graph once per process."""
    graph = laden(einstellungen().abfrage_verzeichnis)
    return json.dumps(graph.buendel(), ensure_ascii=False, separators=(",", ":")).encode()
