"""Serving the built single-page frontend."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

RESERVIERTE_PRAEFIXE = ("api", "kacheln")


def frontend_einbinden(app: FastAPI, verzeichnis: Path) -> None:
    """Serve the files of the built frontend, and its index for every client-side route.

    Paths under the API and the tile proxy are never answered with the index, so
    a mistyped API call fails as a 404 instead of returning HTML.
    """
    index = verzeichnis / "index.html"

    @app.get("/{pfad:path}", include_in_schema=False)
    async def frontend(pfad: str) -> FileResponse:
        if ist_reserviert(pfad) or not index.is_file():
            raise HTTPException(status_code=404)
        datei = (verzeichnis / pfad).resolve()
        if pfad and datei.is_file() and datei.is_relative_to(verzeichnis.resolve()):
            return FileResponse(datei)
        return FileResponse(index)


def ist_reserviert(pfad: str) -> bool:
    """Tell whether a path belongs to the API or the tile proxy."""
    erstes = pfad.split("/", 1)[0]
    return erstes in RESERVIERTE_PRAEFIXE
