"""HTTP route of the named places: what they suggest for a text."""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/orte")


@router.get("/suche")
def suche(request: Request, q: str = "") -> list[dict]:
    """Return the named places matching the text, such as parks, stations and hospitals."""
    return request.app.state.orte.suchen(q[:100])
