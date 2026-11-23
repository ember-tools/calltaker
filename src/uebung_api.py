"""HTTP routes of the exercises: creating, joining, polling the state and sending intents."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from absichten import Absicht, AbsichtAbgelehnt, ausfuehren
from api import abfragegraph
from uebung import Rolle, Uebung, Uebungen, UebungenVoll

router = APIRouter(prefix="/api/uebung")


def uebungen(request: Request) -> Uebungen:
    """Return the exercises of the running application."""
    return request.app.state.uebungen


Alle = Annotated[Uebungen, Depends(uebungen)]


def uebung_zum_code(code: str, alle: Alle) -> tuple[Uebung, Rolle]:
    """Return the exercise and role a code stands for, or answer 404."""
    gefunden = alle.finden(code)
    if gefunden is None:
        raise HTTPException(status_code=404, detail="Diesen Code gibt es nicht.")
    return gefunden


Gefunden = Annotated[tuple[Uebung, Rolle], Depends(uebung_zum_code)]


@router.post("", status_code=201)
async def anlegen(alle: Alle) -> dict[str, str]:
    """Create an exercise and return its two codes."""
    try:
        uebung = alle.anlegen()
    except UebungenVoll as fehler:
        raise HTTPException(status_code=503, detail="Gerade laufen zu viele Übungen.") from fehler
    return {"ausbilderCode": uebung.ausbilder_code, "traineeCode": uebung.trainee_code}


@router.get("/{code}")
async def rolle(gefunden: Gefunden) -> dict[str, str]:
    """Return which role a code stands for."""
    return {"rolle": gefunden[1].value}


@router.get("/{code}/zustand")
async def zustand(gefunden: Gefunden, version: int = 0) -> Response:
    """Return the state as the code's role sees it, or 204 when nothing changed since `version`.

    Every poll counts as a sign of life of its role.
    """
    uebung, rolle_ = gefunden
    uebung.abgefragt(rolle_)
    if version == uebung.version:
        return Response(status_code=204)
    return JSONResponse({"version": uebung.version, "zustand": uebung.zustand(rolle_)})


@router.post("/{code}/absicht")
async def absicht(eingang: Absicht, gefunden: Gefunden) -> dict:
    """Carry out an intent and return its result with the state's new version."""
    uebung, rolle_ = gefunden
    try:
        ergebnis = ausfuehren(uebung, rolle_, eingang, abfragegraph())
    except AbsichtAbgelehnt as fehler:
        raise HTTPException(status_code=fehler.status, detail=str(fehler)) from fehler
    return {"version": uebung.version, "ergebnis": ergebnis}


@router.get("/{code}/pool")
async def pool_herunterladen(gefunden: Gefunden) -> Response:
    """Return the pool as a file to download; only the trainer may."""
    uebung, rolle_ = gefunden
    if rolle_ != Rolle.AUSBILDER:
        raise HTTPException(status_code=403, detail="Den Pool lädt nur der Ausbilder herunter.")
    return JSONResponse(
        uebung.pool.exportieren(abfragegraph()),
        headers={"Content-Disposition": 'attachment; filename="calltaker-pool.json"'},
    )
