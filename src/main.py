"""Entry point of the calltaker server."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from api import abfragebuendel, router
from einstellungen import einstellungen
from fehlermeldung import deutsch
from frontend import frontend_einbinden


@asynccontextmanager
async def lebenszyklus(_: FastAPI) -> AsyncIterator[None]:
    """Load the question graph on start, so a broken graph stops the server instead of a call."""
    abfragebuendel()
    yield


async def ungueltige_anfrage(_: Request, fehler: RequestValidationError) -> JSONResponse:
    """Answer an invalid request with its faults in German."""
    return JSONResponse(status_code=422, content={"detail": deutsch(fehler.errors())})


def anwendung_bauen() -> FastAPI:
    """Build the application with its routes, CORS policy and the built frontend."""
    app = FastAPI(title="Calltaker", lifespan=lebenszyklus)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=einstellungen().erlaubte_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(RequestValidationError, ungueltige_anfrage)
    app.include_router(router)
    frontend_einbinden(app, einstellungen().frontend_verzeichnis)
    return app


app = anwendung_bauen()
