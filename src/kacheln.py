"""The OpenStreetMap tile proxy: tiles fetched once, kept on disk, served to every view.

The OpenStreetMap tile servers ask that clients identify themselves, keep tiles for at least
seven days, never bulk-download and send no more requests than needed. This proxy is that client:
every tile is fetched with the application's own User-Agent and Referer and kept on the data
volume. A tile is fresh for as long as the server's `Cache-Control` or `Expires` says, but never
less than seven days. A stale tile is served at once while it is revalidated in the background
with `If-None-Match`. Requests for the same tile that arrive while it is being fetched wait for
that one fetch. Only zoom levels 10 to 18 inside a box around Berlin are fetched; everything else
is refused without asking upstream.
"""

import asyncio
import contextlib
import email.utils
import json
import logging
import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from version import VERSION

UPSTREAM = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
MIN_ZOOM = 10
MAX_ZOOM = 18
BERLIN = (12.9, 52.25, 13.95, 52.8)
MINDESTENS = 7 * 24 * 3600
BROWSER_CACHE = "public, max-age=86400"
WARTEN_NACH_FEHLER = 300.0
logger = logging.getLogger("calltaker")
HEIMAT = "https://calltaker.chojo.dev"

router = APIRouter()


class KachelNichtErlaubt(Exception):
    """A tile outside the zoom levels or the box this proxy serves."""


class KachelNichtLadbar(Exception):
    """A tile neither the cache nor the tile server can provide."""


@dataclass
class Kachel:
    """A tile's image and how it was fetched."""

    bild: bytes
    etag: str | None
    frisch_bis: float


def kachelbereich(z: int) -> tuple[int, int, int, int]:
    """Return the tile numbers (x from, x to, y from, y to) of the Berlin box at a zoom level."""
    west, sued, ost, nord = BERLIN
    return (*sorted((spalte(west, z), spalte(ost, z))), *sorted((zeile(nord, z), zeile(sued, z))))


def spalte(laenge: float, z: int) -> int:
    """Return the tile column holding a longitude."""
    return int((laenge + 180) / 360 * 2**z)


def zeile(breite: float, z: int) -> int:
    """Return the tile row holding a latitude."""
    rad = math.radians(breite)
    return int((1 - math.asinh(math.tan(rad)) / math.pi) / 2 * 2**z)


def erlaubt(z: int, x: int, y: int) -> bool:
    """Tell whether a tile lies within the zoom levels and the Berlin box."""
    if not MIN_ZOOM <= z <= MAX_ZOOM:
        return False
    x_von, x_bis, y_von, y_bis = kachelbereich(z)
    return x_von <= x <= x_bis and y_von <= y <= y_bis


def frisch_bis(kopf: httpx.Headers, jetzt: float) -> float:
    """Return until when a tile stays fresh: as the server says, but at least seven days."""
    gueltig = jetzt
    treffer = re.search(r"max-age=(\d+)", kopf.get("cache-control", ""))
    if treffer:
        gueltig = jetzt + int(treffer.group(1))
    elif kopf.get("expires"):
        with contextlib.suppress(TypeError, ValueError):
            gueltig = email.utils.parsedate_to_datetime(kopf["expires"]).timestamp()
    return max(gueltig, jetzt + MINDESTENS)


class Kachelcache:
    """Tiles on disk, fetched from OpenStreetMap when missing and revalidated when stale.

    A tile the tile server could not provide is not asked for again for `WARTEN_NACH_FEHLER`
    seconds: a stale copy is kept that long before the next revalidation, and a missing tile is
    refused that long without asking. During an outage or a block the requests per tile therefore
    stay flat instead of growing with the number of views.
    """

    def __init__(
        self,
        verzeichnis: Path,
        client: httpx.AsyncClient,
        uhr: Callable[[], float] = time.time,
    ) -> None:
        """Keep tiles below a folder, fetching them with the given client."""
        self.verzeichnis = verzeichnis
        self.client = client
        self.uhr = uhr
        self._laufend: dict[tuple[int, int, int], asyncio.Task[Kachel]] = {}
        self._hintergrund: set[asyncio.Task[None]] = set()
        self._fehlgeschlagen_bis: dict[tuple[int, int, int], float] = {}

    async def holen(self, z: int, x: int, y: int) -> bytes:
        """Return a tile's image from the cache, fetching or revalidating it as needed."""
        if not erlaubt(z, x, y):
            raise KachelNichtErlaubt
        vorhanden = self._lesen(z, x, y)
        if vorhanden is None:
            if self._fehlgeschlagen_bis.get((z, x, y), 0) > self.uhr():
                raise KachelNichtLadbar
            return (await asyncio.shield(self._einmal_laden(z, x, y, None))).bild
        if vorhanden.frisch_bis < self.uhr():
            aufgabe = asyncio.ensure_future(self._nachpruefen(z, x, y, vorhanden))
            self._hintergrund.add(aufgabe)
            aufgabe.add_done_callback(self._hintergrund.discard)
        return vorhanden.bild

    async def schliessen(self) -> None:
        """Stop every running fetch, before the client they use is closed."""
        aufgaben = [*self._laufend.values(), *self._hintergrund]
        for aufgabe in aufgaben:
            aufgabe.cancel()
        await asyncio.gather(*aufgaben, return_exceptions=True)

    async def _nachpruefen(self, z: int, x: int, y: int, alt: Kachel) -> None:
        """Revalidate a stale tile in the background, logging rather than raising what fails."""
        try:
            await self._einmal_laden(z, x, y, alt)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Kachel %s/%s/%s nicht nachgeprüft", z, x, y)

    def _einmal_laden(self, z: int, x: int, y: int, alt: Kachel | None) -> asyncio.Task[Kachel]:
        """Return the fetch of a tile, starting it unless one is already running."""
        schluessel = (z, x, y)
        laufend = self._laufend.get(schluessel)
        if laufend is not None:
            return laufend
        aufgabe = asyncio.ensure_future(self._laden(z, x, y, alt))
        self._laufend[schluessel] = aufgabe
        aufgabe.add_done_callback(lambda _: self._laufend.pop(schluessel, None))
        return aufgabe

    async def _laden(self, z: int, x: int, y: int, alt: Kachel | None) -> Kachel:
        """Fetch a tile upstream, or confirm the stale copy, and store the result."""
        kopf = {"If-None-Match": alt.etag} if alt and alt.etag else {}
        try:
            antwort = await self.client.get(UPSTREAM.format(z=z, x=x, y=y), headers=kopf)
        except httpx.HTTPError:
            return self._fehlgeschlagen(z, x, y, alt)
        jetzt = self.uhr()
        if antwort.status_code == 304 and alt is not None:
            kachel = Kachel(alt.bild, alt.etag, frisch_bis(antwort.headers, jetzt))
        elif antwort.status_code == 200:
            kachel = Kachel(
                antwort.content, antwort.headers.get("etag"), frisch_bis(antwort.headers, jetzt)
            )
        else:
            return self._fehlgeschlagen(z, x, y, alt)
        self._fehlgeschlagen_bis.pop((z, x, y), None)
        self._schreiben(z, x, y, kachel)
        return kachel

    def _fehlgeschlagen(self, z: int, x: int, y: int, alt: Kachel | None) -> Kachel:
        """Keep a stale copy for a while after a failed fetch, or refuse a missing tile for one."""
        bis = self.uhr() + WARTEN_NACH_FEHLER
        if alt is None:
            jetzt = self.uhr()
            self._fehlgeschlagen_bis = {
                k: v for k, v in self._fehlgeschlagen_bis.items() if v > jetzt
            }
            self._fehlgeschlagen_bis[(z, x, y)] = bis
            raise KachelNichtLadbar
        kachel = Kachel(alt.bild, alt.etag, bis)
        self._schreiben(z, x, y, kachel)
        return kachel

    def _pfad(self, z: int, x: int, y: int) -> Path:
        """Return where a tile's image is kept."""
        return self.verzeichnis / str(z) / str(x) / f"{y}.png"

    def _lesen(self, z: int, x: int, y: int) -> Kachel | None:
        """Read a tile from disk; a missing, broken or incomplete one counts as not there."""
        bild = self._pfad(z, x, y)
        try:
            daten = json.loads(bild.with_suffix(".json").read_text())
            return Kachel(bild.read_bytes(), daten.get("etag"), float(daten["frischBis"]))
        except OSError, ValueError, KeyError, TypeError:
            return None

    def _schreiben(self, z: int, x: int, y: int, kachel: Kachel) -> None:
        """Write a tile to disk, each file through a temporary one, so a crash breaks neither."""
        bild = self._pfad(z, x, y)
        bild.parent.mkdir(parents=True, exist_ok=True)
        ersetzen(bild, kachel.bild)
        meta = json.dumps({"etag": kachel.etag, "frischBis": kachel.frisch_bis})
        ersetzen(bild.with_suffix(".json"), meta.encode())


def ersetzen(datei: Path, inhalt: bytes) -> None:
    """Write a file through a temporary file beside it, so it is never seen half written."""
    zwischen = datei.with_name(datei.name + ".tmp")
    zwischen.write_bytes(inhalt)
    zwischen.replace(datei)


def kachel_client() -> httpx.AsyncClient:
    """Return the client tiles are fetched with, named as the tile usage policy asks."""
    return httpx.AsyncClient(
        timeout=10.0,
        headers={
            "User-Agent": f"calltaker/{VERSION} (+{HEIMAT})",
            "Referer": f"{HEIMAT}/",
        },
    )


@router.get("/kacheln/{z}/{x}/{y}.png")
async def kachel(z: int, x: int, y: int, request: Request) -> Response:
    """Return a map tile of Berlin from the cache, fetching it from OpenStreetMap when needed."""
    cache: Kachelcache = request.app.state.kachelcache
    try:
        bild = await cache.holen(z, x, y)
    except KachelNichtErlaubt as fehler:
        raise HTTPException(status_code=404, detail="Diese Kachel gibt es hier nicht.") from fehler
    except KachelNichtLadbar as fehler:
        raise HTTPException(
            status_code=502, detail="Die Kachel ist gerade nicht ladbar."
        ) from fehler
    return Response(content=bild, media_type="image/png", headers={"Cache-Control": BROWSER_CACHE})
