import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

import kacheln
from kacheln import (
    CLIENT_MISS_BURST,
    CLIENT_MISSES_PER_SECOND,
    GLOBAL_MISS_BURST,
    MINDESTENS,
    WARTEN_NACH_FEHLER,
    Kachelcache,
    KachelNichtErlaubt,
    KachelNichtLadbar,
    MissBudget,
    TileRateLimited,
    erlaubt,
    frisch_bis,
    kachelbereich,
    spalte,
    zeile,
)
from main import anwendung_bauen

BERLIN_MITTE = (14, spalte(13.4, 14), zeile(52.52, 14))


class Uhr:
    """A clock the test moves by hand."""

    def __init__(self) -> None:
        """Start at a fixed time."""
        self.jetzt = 1_000_000.0

    def __call__(self) -> float:
        """Return the current time."""
        return self.jetzt


class Upstream:
    """A stand-in for the tile server that counts what it is asked."""

    def __init__(self) -> None:
        """Answer with a tile by default."""
        self.anfragen: list[httpx.Request] = []
        self.antwort = lambda anfrage: httpx.Response(200, content=b"PNG1", headers={"ETag": '"a"'})

    def __call__(self, anfrage: httpx.Request) -> httpx.Response:
        """Record the request and answer it."""
        self.anfragen.append(anfrage)
        return self.antwort(anfrage)


@pytest.fixture
def upstream():
    return Upstream()


@pytest.fixture
def uhr():
    return Uhr()


def cache_mit(tmp_path, upstream, uhr):
    client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    return Kachelcache(tmp_path, client, uhr)


def holen(cache, *kachel):
    async def ablauf():
        bild = await cache.holen(*kachel)
        await asyncio.gather(*cache._hintergrund)
        return bild

    return asyncio.run(ablauf())


def test_nur_berlin_in_den_erlaubten_zoomstufen():
    z, x, y = BERLIN_MITTE
    assert erlaubt(z, x, y)
    assert not erlaubt(9, x >> 5, y >> 5)
    assert not erlaubt(19, x * 32, y * 32)
    x_von, x_bis, y_von, y_bis = kachelbereich(14)
    assert not erlaubt(14, x_bis + 1, y)
    assert not erlaubt(14, x, y_von - 1)


def test_eine_kachel_wird_einmal_geholt_und_dann_vom_cache_geliefert(tmp_path, upstream, uhr):
    cache = cache_mit(tmp_path, upstream, uhr)
    assert holen(cache, *BERLIN_MITTE) == b"PNG1"
    assert holen(cache, *BERLIN_MITTE) == b"PNG1"
    assert len(upstream.anfragen) == 1
    assert upstream.anfragen[0].url.path == "/{}/{}/{}.png".format(*BERLIN_MITTE)


def test_eine_alte_kachel_kommt_sofort_und_wird_nachgeprueft(tmp_path, upstream, uhr):
    cache = cache_mit(tmp_path, upstream, uhr)
    holen(cache, *BERLIN_MITTE)
    uhr.jetzt += MINDESTENS + 1
    upstream.antwort = lambda anfrage: httpx.Response(304, headers={"Cache-Control": "max-age=60"})
    assert holen(cache, *BERLIN_MITTE) == b"PNG1"
    assert upstream.anfragen[-1].headers["If-None-Match"] == '"a"'
    holen(cache, *BERLIN_MITTE)
    assert len(upstream.anfragen) == 2


def test_gleichzeitige_anfragen_teilen_sich_einen_abruf(tmp_path, upstream, uhr):
    cache = cache_mit(tmp_path, upstream, uhr)

    async def alle():
        return await asyncio.gather(*(cache.holen(*BERLIN_MITTE) for _ in range(5)))

    assert asyncio.run(alle()) == [b"PNG1"] * 5
    assert len(upstream.anfragen) == 1


def test_bei_einem_ausfall_bleibt_die_alte_kachel(tmp_path, upstream, uhr):
    cache = cache_mit(tmp_path, upstream, uhr)
    holen(cache, *BERLIN_MITTE)
    uhr.jetzt += MINDESTENS + 1

    def ausfall(anfrage):
        raise httpx.ConnectError("weg", request=anfrage)

    upstream.antwort = ausfall
    assert holen(cache, *BERLIN_MITTE) == b"PNG1"


def test_ohne_kachel_und_ohne_server_gibt_es_nichts(tmp_path, upstream, uhr):
    upstream.antwort = lambda anfrage: httpx.Response(503)
    cache = cache_mit(tmp_path, upstream, uhr)
    with pytest.raises(KachelNichtLadbar):
        holen(cache, *BERLIN_MITTE)
    with pytest.raises(KachelNichtErlaubt):
        holen(cache, 3, 4, 2)
    assert len(upstream.anfragen) == 1


def test_eine_kachel_bleibt_mindestens_sieben_tage_frisch():
    jetzt = 1000.0
    assert frisch_bis(httpx.Headers({"Cache-Control": "max-age=60"}), jetzt) == jetzt + MINDESTENS
    lang = 30 * 24 * 3600
    assert frisch_bis(httpx.Headers({"Cache-Control": f"max-age={lang}"}), jetzt) == jetzt + lang
    assert frisch_bis(httpx.Headers({}), jetzt) == jetzt + MINDESTENS


def test_der_client_nennt_sich_wie_verlangt():
    client = kacheln.kachel_client()
    assert client.headers["User-Agent"].startswith("calltaker/")
    assert "https://calltaker.emberbox.app" in client.headers["User-Agent"]
    assert client.headers["Referer"] == "https://calltaker.emberbox.app/"


def test_die_route_liefert_kacheln_und_lehnt_fremde_ab(tmp_path, upstream, uhr):
    with TestClient(anwendung_bauen()) as client:
        client.app.state.kachelcache = cache_mit(tmp_path, upstream, uhr)
        gut = client.get("/kacheln/{}/{}/{}.png".format(*BERLIN_MITTE))
        fremd = client.get("/kacheln/3/4/2.png")
        upstream.antwort = lambda anfrage: httpx.Response(500)
        z, x, y = BERLIN_MITTE
        kaputt = client.get(f"/kacheln/{z}/{x + 1}/{y}.png")
    assert gut.status_code == 200
    assert gut.headers["content-type"] == "image/png"
    assert gut.headers["cache-control"] == "public, max-age=86400"
    assert fremd.status_code == 404
    assert fremd.json() == {"detail": "Diese Kachel gibt es hier nicht."}
    assert kaputt.status_code == 502


def test_kaputte_metadaten_lassen_die_kachel_neu_holen(tmp_path, upstream, uhr):
    cache = cache_mit(tmp_path, upstream, uhr)
    holen(cache, *BERLIN_MITTE)
    meta = tmp_path.joinpath(*map(str, BERLIN_MITTE[:2]), f"{BERLIN_MITTE[2]}.json")
    meta.write_text('{"etag": ')
    assert holen(cache, *BERLIN_MITTE) == b"PNG1"
    assert len(upstream.anfragen) == 2


def test_nach_einem_fehler_wird_eine_weile_nicht_gefragt(tmp_path, upstream, uhr):
    cache = cache_mit(tmp_path, upstream, uhr)
    holen(cache, *BERLIN_MITTE)
    uhr.jetzt += MINDESTENS + 1
    upstream.antwort = lambda anfrage: httpx.Response(429)
    for _ in range(3):
        assert holen(cache, *BERLIN_MITTE) == b"PNG1"
    assert len(upstream.anfragen) == 2
    uhr.jetzt += WARTEN_NACH_FEHLER + 1
    holen(cache, *BERLIN_MITTE)
    assert len(upstream.anfragen) == 3


def test_eine_fehlende_kachel_wird_nach_einem_fehler_eine_weile_abgelehnt(tmp_path, upstream, uhr):
    upstream.antwort = lambda anfrage: httpx.Response(403)
    cache = cache_mit(tmp_path, upstream, uhr)
    for _ in range(3):
        with pytest.raises(KachelNichtLadbar):
            holen(cache, *BERLIN_MITTE)
    assert len(upstream.anfragen) == 1


def test_eine_neue_kachel_ersetzt_die_alte(tmp_path, upstream, uhr):
    cache = cache_mit(tmp_path, upstream, uhr)
    holen(cache, *BERLIN_MITTE)
    uhr.jetzt += MINDESTENS + 1
    upstream.antwort = lambda anfrage: httpx.Response(200, content=b"PNG2", headers={"ETag": '"b"'})
    assert holen(cache, *BERLIN_MITTE) == b"PNG1"
    assert holen(cache, *BERLIN_MITTE) == b"PNG2"
    uhr.jetzt += MINDESTENS + 1
    holen(cache, *BERLIN_MITTE)
    assert upstream.anfragen[-1].headers["If-None-Match"] == '"b"'


def test_expires_gilt_und_max_age_geht_vor():
    jetzt = 1_000_000.0
    spaeter = "Thu, 01 Jan 2099 00:00:00 GMT"
    assert frisch_bis(httpx.Headers({"Expires": spaeter}), jetzt) > jetzt + MINDESTENS
    beides = httpx.Headers({"Expires": spaeter, "Cache-Control": "max-age=60"})
    assert frisch_bis(beides, jetzt) == jetzt + MINDESTENS


def test_schliessen_beendet_laufende_abrufe(tmp_path, uhr):
    async def nie(anfrage):
        await asyncio.sleep(3600)

    client = httpx.AsyncClient(transport=httpx.MockTransport(nie))
    cache = Kachelcache(tmp_path, client, uhr)

    async def ablauf():
        abruf = asyncio.ensure_future(cache.holen(*BERLIN_MITTE))
        await asyncio.sleep(0)
        await cache.schliessen()
        with pytest.raises(asyncio.CancelledError):
            await abruf

    asyncio.run(ablauf())


def test_a_client_fetches_only_a_limited_number_of_new_tiles(tmp_path, upstream, uhr):
    cache = cache_mit(tmp_path, upstream, uhr)
    z, x, y = BERLIN_MITTE
    for step in range(CLIENT_MISS_BURST):
        holen(cache, z, x + step % 10, y + step // 10, "1.2.3.4")
    with pytest.raises(TileRateLimited):
        holen(cache, z, x, y + 7, "1.2.3.4")
    assert len(upstream.anfragen) == CLIENT_MISS_BURST
    assert holen(cache, z, x, y + 7, "5.6.7.8") == b"PNG1"


def test_a_cached_tile_costs_nothing_from_the_budget(tmp_path, upstream, uhr):
    cache = cache_mit(tmp_path, upstream, uhr)
    for _ in range(CLIENT_MISS_BURST + 5):
        assert holen(cache, *BERLIN_MITTE, "1.2.3.4") == b"PNG1"
    assert len(upstream.anfragen) == 1


def test_the_budget_refills_over_time(uhr):
    budget = MissBudget(uhr)
    for _ in range(CLIENT_MISS_BURST):
        assert budget.take("a")
    assert not budget.take("a")
    uhr.jetzt += 1 / CLIENT_MISSES_PER_SECOND
    assert budget.take("a")
    assert not budget.take("a")


def test_all_clients_share_one_overall_budget(uhr):
    budget = MissBudget(uhr)
    for number in range(GLOBAL_MISS_BURST):
        assert budget.take(f"client-{number}")
    assert not budget.take("one-more")


def test_the_route_answers_429_once_the_budget_is_used_up(tmp_path, upstream, uhr):
    with TestClient(anwendung_bauen()) as client:
        cache = cache_mit(tmp_path, upstream, uhr)
        client.app.state.kachelcache = cache
        cache._budget.take = lambda client: False
        response = client.get("/kacheln/{}/{}/{}.png".format(*BERLIN_MITTE))
    assert response.status_code == 429
    assert response.headers["retry-after"] == "10"
    assert upstream.anfragen == []
