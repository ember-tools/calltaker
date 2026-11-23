from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from frontend import frontend_einbinden
from main import app


def test_gesundheit():
    antwort = TestClient(app).get("/api/gesundheit")
    assert antwort.status_code == 200
    assert antwort.json() == {"status": "ok"}


def _frontend_app(tmp_path: Path) -> TestClient:
    verzeichnis = tmp_path / "dist"
    (verzeichnis / "assets").mkdir(parents=True)
    (verzeichnis / "index.html").write_text("<!doctype html><title>index</title>")
    (verzeichnis / "assets" / "app.js").write_text("console.info(1)")
    (tmp_path / "geheim.txt").write_text("geheim")
    app = FastAPI()
    frontend_einbinden(app, verzeichnis)
    return TestClient(app)


def test_frontend_liefert_dateien_und_index(tmp_path):
    client = _frontend_app(tmp_path)
    assert client.get("/assets/app.js").text == "console.info(1)"
    assert "index" in client.get("/a/A-3KX9").text
    assert "index" in client.get("/").text


def test_frontend_beantwortet_api_pfade_nicht(tmp_path):
    client = _frontend_app(tmp_path)
    for pfad in ("/api", "/api/unbekannt", "/kacheln", "/kacheln/1/2/3.png"):
        assert client.get(pfad).status_code == 404, pfad


def test_frontend_verlaesst_das_verzeichnis_nicht(tmp_path):
    client = _frontend_app(tmp_path)
    antwort = client.get("/..%2Fgeheim.txt")
    assert "geheim" not in antwort.text
    assert "index" in antwort.text
