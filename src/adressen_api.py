"""HTTP routes of the address list: whether it is there, what it suggests, and random addresses."""

import random

from fastapi import APIRouter, HTTPException, Request

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


@router.get("/zufall")
def zufall(request: Request, ortsteil: str = "", bezirk: str = "") -> dict:
    """Return a random address, optionally within an Ortsteil or a Bezirk."""
    adresse = adressen(request).zufall(random.Random(), ortsteil[:80], bezirk[:80])
    if adresse is None:
        raise HTTPException(status_code=404, detail="Keine Adresse gefunden.")
    return adresse


@router.get("/gebiete")
def gebiete(request: Request) -> dict[str, list[str]]:
    """Return the Bezirke with their Ortsteile, for choosing where addresses are drawn from."""
    return adressen(request).gebiete()
