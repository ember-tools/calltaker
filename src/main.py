"""Entry point of the calltaker server."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import router
from einstellungen import einstellungen
from frontend import frontend_einbinden


def anwendung_bauen() -> FastAPI:
    """Build the application with its routes, CORS policy and the built frontend."""
    app = FastAPI(title="Calltaker")
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
