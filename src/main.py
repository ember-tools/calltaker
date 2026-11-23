"""Entry point of the calltaker server."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

import kacheln
import uebung_api
from api import abfragebuendel, router
from einstellungen import einstellungen
from fehlermeldung import deutsch
from frontend import frontend_einbinden
from grenzen import KoerperGrenze
from uebung import Uebungen

AUFRAEUMEN_ALLE = 60
logger = logging.getLogger("calltaker")
ANFRAGE_HOECHSTENS = 2 * 1024 * 1024


@asynccontextmanager
async def lebenszyklus(app: FastAPI) -> AsyncIterator[None]:
    """Load the question graph on start and keep the exercises tidy while the server runs.

    A broken graph stops the server instead of a call. Once a second every exercise updates who
    counts as connected and moves its queue on; once a minute exercises nobody has polled for too
    long are dropped.
    """
    abfragebuendel()
    client = kacheln.kachel_client()
    app.state.kachelcache = kacheln.Kachelcache(
        einstellungen().daten_verzeichnis / "kacheln", client
    )
    aufgabe = asyncio.create_task(pflegen(app.state.uebungen))
    yield
    aufgabe.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await aufgabe
    await app.state.kachelcache.schliessen()
    await client.aclose()


async def pflegen(uebungen: Uebungen) -> None:
    """Update connections and queues every second, and drop stale exercises every minute."""
    takt = 0
    while True:
        await asyncio.sleep(1)
        for uebung in uebungen.alle():
            try:
                uebung.verbindungen_pruefen()
                uebung.engine.takt()
            except Exception:
                logger.exception("Pflege der Übung %s fehlgeschlagen", uebung.kennung)
        takt += 1
        if takt % AUFRAEUMEN_ALLE == 0:
            uebungen.aufraeumen()


async def ungueltige_anfrage(_: Request, fehler: RequestValidationError) -> JSONResponse:
    """Answer an invalid request with its faults in German."""
    return JSONResponse(status_code=422, content={"detail": deutsch(fehler.errors())})


def anwendung_bauen() -> FastAPI:
    """Build the application with its routes, CORS policy and the built frontend."""
    app = FastAPI(title="Calltaker", lifespan=lebenszyklus)
    app.state.uebungen = Uebungen(
        hoechstens=einstellungen().uebungen_hoechstens,
        frist=einstellungen().uebung_lebensdauer_stunden * 3600,
    )
    app.add_middleware(KoerperGrenze, hoechstens=ANFRAGE_HOECHSTENS)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=einstellungen().erlaubte_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(RequestValidationError, ungueltige_anfrage)
    app.include_router(router)
    app.include_router(uebung_api.router)
    app.include_router(kacheln.router)
    frontend_einbinden(app, einstellungen().frontend_verzeichnis)
    return app


app = anwendung_bauen()
