"""HTTP routes of the address list: whether it is there, and what it suggests for a text."""

from fastapi import APIRouter, Request

from adressen import Adressen

router = APIRouter(prefix="/api/adressen")


def adressen(request: Request) -> Adressen:
    """Return the address list of the running application."""
    return request.app.state.adressen


@router.get("/status")
def status(request: Request) -> dict:
    """Return whether the list is there, so the views know whether to offer completion."""
    return adressen(request).bestand()


@router.get("/suche")
def suche(request: Request, q: str = "") -> list[dict]:
    """Return streets while a name is typed, and doors once a house number follows it."""
    return adressen(request).suchen(q[:100])
