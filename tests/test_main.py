from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from frontend import mount_frontend
from main import app


def test_gesundheit():
    antwort = TestClient(app).get("/api/gesundheit")
    assert antwort.status_code == 200
    assert antwort.json() == {"status": "ok"}


def _frontend_app(tmp_path: Path) -> TestClient:
    verzeichnis = tmp_path / "dist"
    (verzeichnis / "assets").mkdir(parents=True)
    (verzeichnis / "pages" / "hilfe").mkdir(parents=True)
    (verzeichnis / "index.html").write_text("<!doctype html><title>index</title>")
    (verzeichnis / "pages" / "index.html").write_text("<!doctype html><title>start</title>")
    (verzeichnis / "pages" / "hilfe" / "index.html").write_text(
        "<!doctype html><title>hilfe</title>"
    )
    (verzeichnis / "build.json").write_text("{}")
    (verzeichnis / "manifest.webmanifest").write_text("{}")
    (verzeichnis / "assets" / "app.js").write_text("console.info(1)")
    (tmp_path / "geheim.txt").write_text("geheim")
    app = FastAPI()
    mount_frontend(app, verzeichnis)
    return TestClient(app)


def test_frontend_liefert_dateien_und_index(tmp_path):
    client = _frontend_app(tmp_path)
    assert client.get("/assets/app.js").text == "console.info(1)"
    assert "index" in client.get("/a/A-3KX9").text


def test_frontend_beantwortet_api_pfade_nicht(tmp_path):
    client = _frontend_app(tmp_path)
    for pfad in ("/api", "/api/unbekannt", "/kacheln", "/kacheln/1/2/3.png"):
        assert client.get(pfad).status_code == 404, pfad


def test_frontend_verlaesst_das_verzeichnis_nicht(tmp_path):
    client = _frontend_app(tmp_path)
    antwort = client.get("/..%2Fgeheim.txt")
    assert "geheim" not in antwort.text
    assert "index" in antwort.text


def test_frontend_serves_prerendered_pages_for_indexing(tmp_path):
    client = _frontend_app(tmp_path)
    for path, title in (("/", "start"), ("/hilfe", "hilfe"), ("/hilfe/", "hilfe")):
        response = client.get(path)
        assert title in response.text, path
        assert "x-robots-tag" not in response.headers, path


def test_frontend_serves_the_manifest_with_its_media_type(tmp_path):
    response = _frontend_app(tmp_path).get("/manifest.webmanifest")
    assert response.headers["content-type"] == "application/manifest+json"


def test_frontend_keeps_the_shell_out_of_search_engines(tmp_path):
    client = _frontend_app(tmp_path)
    response = client.get("/a/A-3KX9")
    assert response.headers["x-robots-tag"] == "noindex, nofollow"


def test_frontend_serves_each_page_at_one_address_only(tmp_path):
    client = _frontend_app(tmp_path)
    for pfad in (
        "/index.html",
        "/pages/index.html",
        "/pages/hilfe/index.html",
        "/./index.html",
        "/hilfe/../index.html",
    ):
        antwort = client.get(pfad)
        assert "<title>index</title>" in antwort.text, pfad
        assert antwort.headers["x-robots-tag"] == "noindex, nofollow", pfad


def test_frontend_serves_build_json_uncached(tmp_path):
    client = _frontend_app(tmp_path)
    assert client.get("/build.json").headers["cache-control"] == "no-store"


def test_frontend_answers_a_missing_asset_with_404(tmp_path):
    client = _frontend_app(tmp_path)
    assert client.get("/assets/old-build-1234.js").status_code == 404
