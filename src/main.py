"""Entry point of the calltaker server."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api import abfragebuendel, router
from einstellungen import einstellungen
from frontend import frontend_einbinden


@asynccontextmanager
async def lebenszyklus(_: FastAPI) -> AsyncIterator[None]:
    """Load the question graph on start, so a broken graph stops the server instead of a call."""
    abfragebuendel()
    yield


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
    app.include_router(router)
    frontend_einbinden(app, einstellungen().frontend_verzeichnis)
    return app


app = anwendung_bauen()
