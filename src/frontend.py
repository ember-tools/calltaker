"""Serving the built frontend: prerendered public pages, built files and the single-page shell."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

RESERVED_PREFIXES = ("api", "kacheln")
PAGES = "pages"


def mount_frontend(app: FastAPI, directory: Path) -> None:
    """Serve the built frontend for every path outside the API and the tile proxy.

    Paths under the API and the tile proxy are never answered with HTML, so a mistyped API call
    fails as a 404. Everything else is answered by `frontend_response`.
    """

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str) -> FileResponse:
        if is_reserved(path) or not (directory / "index.html").is_file():
            raise HTTPException(status_code=404)
        return frontend_response(directory, path)


def frontend_response(directory: Path, path: str) -> FileResponse:
    """Resolve a path to a prerendered page, a built file or the single-page shell.

    A prerendered page (`/`, `/hilfe` and the help topics below it) comes from
    `pages/<path>/index.html`. A built file is served as it is, except the shell itself and the
    prerendered pages under their file names, so each page has one address. `build.json` is never
    cached, so open pages notice a new build. A missing file under `assets/` is a 404 rather than
    the shell, so a page still running an older build sees its chunk fail to load instead of
    receiving HTML.
    Every other path gets the shell, which search engines are told not to index: its content
    depends on an exercise code, and only the prerendered pages are meant for them. Paths are
    resolved before they are checked, so dot segments cannot reach around these rules.
    """
    root = directory.resolve()
    pages = root / PAGES
    page = (pages / path.strip("/") / "index.html").resolve()
    if page.is_relative_to(pages) and page.is_file():
        return FileResponse(page)
    candidate = (root / path.strip("/")).resolve()
    if candidate.is_relative_to(root) and candidate != root and candidate.is_file():
        relative = candidate.relative_to(root)
        if relative != Path("index.html") and relative.parts[0] != PAGES:
            headers = {"Cache-Control": "no-store"} if relative == Path("build.json") else None
            return FileResponse(candidate, headers=headers)
    if path.strip("/").split("/", 1)[0] == "assets":
        raise HTTPException(status_code=404)
    return FileResponse(root / "index.html", headers={"X-Robots-Tag": "noindex, nofollow"})


def is_reserved(path: str) -> bool:
    """Tell whether a path belongs to the API or the tile proxy."""
    first = path.split("/", 1)[0]
    return first in RESERVED_PREFIXES
