"""A limit on the size of request bodies, so nobody can fill the server's memory with one upload."""

from fastapi import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

ZU_GROSS = "Die Anfrage ist zu groß."


class KoerperGrenze:
    """Refuse a request whose body is larger than allowed, with a German reason.

    The declared length is checked first and answered here. A body without one, or one that is
    longer than it claims, is counted while it arrives; once it grows too large the read fails
    with an HTTP 413, which the application answers like any other refusal.
    """

    def __init__(self, app: ASGIApp, hoechstens: int) -> None:
        """Wrap an application with the limit in bytes."""
        self.app = app
        self.hoechstens = hoechstens

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass the request on, or refuse it once it grows beyond the limit."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        laenge = dict(scope.get("headers", [])).get(b"content-length")
        if laenge is not None and laenge.isdigit() and int(laenge) > self.hoechstens:
            await zu_gross(send)
            return
        gelesen = 0

        async def zaehlend() -> Message:
            nonlocal gelesen
            nachricht = await receive()
            gelesen += len(nachricht.get("body", b""))
            if gelesen > self.hoechstens:
                raise HTTPException(status_code=413, detail=ZU_GROSS)
            return nachricht

        await self.app(scope, zaehlend, send)


async def zu_gross(send: Send) -> None:
    """Answer 413 with the reason in German."""
    koerper = f'{{"detail":"{ZU_GROSS}"}}'.encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(koerper)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": koerper})
