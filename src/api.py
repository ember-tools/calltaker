"""HTTP routes of the server."""

from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/gesundheit")
async def gesundheit() -> dict[str, str]:
    """Report that the server is up."""
    return {"status": "ok"}
