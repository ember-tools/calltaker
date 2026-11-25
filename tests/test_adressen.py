import random

import httpx
import pytest
from fastapi.testclient import TestClient

import adressen as adressen_modul
from adressen import (
    Adressen,
    LadenAbgebrochen,
    UnvollstaendigeListe,
    hausnummer,
    suchformen,
    zerlegen,
)
from main import adressen_holen, anwendung_bauen


def merkmal(strasse, hnr, zusatz, plz, ortsteil, bezirk, laenge, breite):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [laenge, breite]},
        "properties": {
            "str_name": strasse,
            "hnr": hnr,
            "hnr_zusatz": zusatz,
            "plz": plz,
            "ort_name": ortsteil,
            "bez_name": bezirk,
        },
    }


MERKMALE = [
    merkmal("Karl-Marx-Straße", 92, None, "12043", "Neukölln", "Neukölln", 13.4385, 52.4793),
    merkmal("Karl-Marx-Straße", 92, "a", "12043", "Neukölln", "Neukölln", 13.4386, 52.4794),
    merkmal("Karl-Marx-Straße", 200, None, "12055", "Neukölln", "Neukölln", 13.44, 52.47),
    merkmal(
        "Karl-Marx-Allee",
        92,
        None,
        "10243",
        "Friedrichshain",
        "Friedrichshain-Kreuzberg",
        13.43,
        52.51,
    ),
    merkmal("Werderstraße", 20, None, "13587", "Hakenfelde", "Spandau", 13.2122, 52.5663),
    merkmal(
        "Stralauer Allee",
        1,
        None,
        "10245",
        "Friedrichshain",
        "Friedrichshain-Kreuzberg",
        13.45,
        52.5,
    ),
    {"type": "Feature", "geometry": None, "properties": {"str_name": "Ohne Punkt", "hnr": 1}},
]


def wfs_mit(seiten, gemeldet=None):
    anfragen = []

    def wfs(anfrage: httpx.Request) -> httpx.Response:
        anfragen.append(anfrage)
        nummer = len(anfragen) - 1
        daten = {"features": seiten[nummer] if nummer < len(seiten) else []}
        if gemeldet is not None:
            daten["numberMatched"] = gemeldet
        return httpx.Response(200, json=daten)

    return httpx.Client(transport=httpx.MockTransport(wfs)), anfragen


@pytest.fixture
def adressen(tmp_path):
    client, anfragen = wfs_mit([MERKMALE])
    liste = Adressen(tmp_path / "adressen.sqlite")
    assert liste.laden(client) == 6
    assert anfragen[0].url.params["SRSNAME"] == "EPSG:4326"
    assert len(anfragen) == 1
    return liste


def test_ohne_liste_gibt_es_nichts(tmp_path):
    leer = Adressen(tmp_path / "fehlt.sqlite")
    assert leer.bestand() == {"verfuegbar": False, "anzahl": 0, "stand": None}
    assert leer.veraltet()
    assert leer.suchen("Karl") == []
    assert leer.zufall(random.Random(1)) is None


def test_der_bestand_ist_frisch(adressen):
    assert adressen.bestand()["anzahl"] == 6
    assert not adressen.veraltet()


def test_ohne_hausnummer_kommen_strassen(adressen):
    treffer = adressen.suchen("karl-marx")
    assert [t["beschriftung"] for t in treffer] == [
        "Karl-Marx-Allee, 10243 Friedrichshain",
        "Karl-Marx-Straße, 12043 Neukölln",
        "Karl-Marx-Straße, 12055 Neukölln",
    ]
    assert "breite" not in treffer[0]


def test_mit_hausnummer_kommen_tueren_mit_koordinaten(adressen):
    treffer = adressen.suchen("Karl-Marx-Str 92")
    assert [t["beschriftung"] for t in treffer] == [
        "Karl-Marx-Straße 92, 12043 Neukölln",
        "Karl-Marx-Straße 92A, 12043 Neukölln",
    ]
    assert (treffer[0]["breite"], treffer[0]["laenge"]) == (52.4793, 13.4385)
    assert treffer[0]["bezirk"] == "Neukölln"
    assert [t["hausnummer"] for t in adressen.suchen("Karl-Marx-Straße 92 a")] == ["92A"]


def test_zu_kurze_eingaben_finden_nichts(adressen):
    assert adressen.suchen("K") == []


def test_zufallsadressen_im_ortsteil_oder_bezirk(adressen):
    zufall = random.Random(3)
    assert adressen.zufall(zufall, ortsteil="Hakenfelde")["strasse"] == "Werderstraße"
    assert (
        adressen.zufall(zufall, bezirk="Friedrichshain-Kreuzberg")["strasse"] == "Karl-Marx-Allee"
    )
    assert adressen.zufall(zufall, ortsteil="Gibtesnicht") is None
    assert adressen.zufall(zufall)["breite"] > 52


def test_ein_abgebrochener_abruf_laesst_die_alte_liste_stehen(adressen):
    def kaputt(anfrage):
        return httpx.Response(500)

    with pytest.raises(httpx.HTTPStatusError):
        adressen.laden(httpx.Client(transport=httpx.MockTransport(kaputt)))
    assert adressen.bestand()["anzahl"] == 6


@pytest.mark.parametrize(
    ("text", "erwartet"),
    [
        ("Archenholdstr 21", ("Archenholdstr", "21", "")),
        ("Straße des 17. Juni", ("Straße des 17. Juni", "", "")),
        ("Werderstraße, 20b", ("Werderstraße", "20b", "")),
        ("Werderstraße 20 b", ("Werderstraße", "20 b", "")),
        ("Sieg 25 bies", ("Sieg", "25", "bies")),
        ("Sieg 25b Biesdorf", ("Sieg", "25b", "Biesdorf")),
        ("Karl-Marx-Str 92, 12043", ("Karl-Marx-Str", "92", "12043")),
    ],
)
def test_zerlegen(text, erwartet):
    assert zerlegen(text) == erwartet


def test_suchformen_und_hausnummer():
    assert suchformen("Karl-Marx-Str.") == ["karl-marx-str.", "karl-marx-straße"]
    assert suchformen("Lindenstrasse") == ["lindenstrasse", "lindenstraße"]
    assert suchformen("Str") == ["str"]
    assert hausnummer("28 a") == (28, "A")
    assert hausnummer("x") == (None, "")


def test_die_routen_fragen_die_liste(adressen):
    with TestClient(anwendung_bauen()) as client:
        client.app.state.adressen = adressen
        status = client.get("/api/adressen/status").json()
        treffer = client.get("/api/adressen/suche", params={"q": "Werderstr 20"}).json()
    assert status["verfuegbar"] is True
    assert treffer[0]["beschriftung"] == "Werderstraße 20, 13587 Hakenfelde"


def test_die_naechste_tuer_ueber_die_route(adressen):
    with TestClient(anwendung_bauen()) as client:
        client.app.state.adressen = adressen
        nah = client.get("/api/adressen/naechste", params={"breite": 52.5664, "laenge": 13.2123})
        fern = client.get("/api/adressen/naechste", params={"breite": 52.0, "laenge": 13.0})
    assert nah.json()["beschriftung"] == "Werderstraße 20, 13587 Hakenfelde"
    assert fern.json() is None


def test_str_am_anfang_findet_weiter_alle_strassen(adressen):
    assert [t["strasse"] for t in adressen.suchen("Str")] == ["Stralauer Allee"]
    assert [t["strasse"] for t in adressen.suchen("Werderstr")] == ["Werderstraße"]


def test_platzhalter_werden_woertlich_genommen(adressen):
    assert adressen.suchen("%%") == []
    assert adressen.suchen("K_rl") == []


def test_die_suche_nutzt_den_index(adressen):
    import sqlite3

    from adressen import praefix

    bedingung, werte = praefix(["karl"])
    with sqlite3.connect(adressen.datei) as verbindung:
        plan = verbindung.execute(
            f"EXPLAIN QUERY PLAN SELECT * FROM adressen WHERE {bedingung}", werte
        ).fetchall()
    assert "USING INDEX adressen_suche" in str(plan)


def test_es_wird_seitenweise_nach_rohzahl_geladen(tmp_path, monkeypatch):
    monkeypatch.setattr(adressen_modul, "SEITE", 3)
    kaputt = {"type": "Feature", "geometry": None, "properties": {}}
    client, anfragen = wfs_mit([MERKMALE[:3], [kaputt, kaputt, kaputt], MERKMALE[3:5]])
    assert Adressen(tmp_path / "a.sqlite").laden(client) == 5
    assert [a.url.params["STARTINDEX"] for a in anfragen] == ["0", "3", "6"]


@pytest.mark.parametrize(
    ("seiten", "gemeldet", "meldung"),
    [
        ([[]], None, "keine Adressen"),
        ([MERKMALE], 1000, "von gemeldeten 1000"),
        ([MERKMALE[:2]], None, "bisher 6"),
    ],
)
def test_ein_zu_kleiner_abruf_ersetzt_nichts(adressen, seiten, gemeldet, meldung):
    client, _ = wfs_mit(seiten, gemeldet)
    with pytest.raises(UnvollstaendigeListe, match=meldung):
        adressen.laden(client)
    assert adressen.bestand()["anzahl"] == 6
    assert list(adressen.datei.parent.glob("*.neu")) == []


def test_ein_stopp_bricht_das_laden_ab(tmp_path):
    import threading

    stopp = threading.Event()
    stopp.set()
    client, anfragen = wfs_mit([MERKMALE])
    with pytest.raises(LadenAbgebrochen):
        Adressen(tmp_path / "a.sqlite").laden(client, stopp)
    assert anfragen == []
    assert list(tmp_path.iterdir()) == []


def test_das_hintergrundladen_meldet_was_geschah(adressen, tmp_path, monkeypatch, caplog):
    import asyncio
    import threading

    from einstellungen import einstellungen

    stopp = threading.Event()
    assert asyncio.run(adressen_holen(adressen, stopp)) == "aus"
    monkeypatch.setattr(einstellungen(), "adressen_laden", True)
    assert asyncio.run(adressen_holen(adressen, stopp)) == "frisch"
    kaputt = Adressen(tmp_path / "kaputt.sqlite")
    kaputt.datei.write_text("keine Datenbank")
    assert kaputt.bestand()["verfuegbar"] is False
    monkeypatch.setattr(kaputt, "laden", lambda client, stopp: 7)
    assert asyncio.run(adressen_holen(kaputt, stopp)) == "geladen"

    def scheitern(client, stopp):
        raise UnvollstaendigeListe("leer")

    monkeypatch.setattr(kaputt, "laden", scheitern)
    assert asyncio.run(adressen_holen(kaputt, stopp)) == "fehler"
    assert "Adressverzeichnis nicht geladen" in caplog.text


def test_zufall_und_gebiete_ueber_die_routen(adressen):
    with TestClient(anwendung_bauen()) as client:
        client.app.state.adressen = adressen
        zufall = client.get("/api/adressen/zufall", params={"bezirk": "Spandau"}).json()
        keine = client.get("/api/adressen/zufall", params={"ortsteil": "Atlantis"})
        gebiete = client.get("/api/adressen/gebiete").json()
    assert zufall["strasse"] == "Werderstraße"
    assert keine.status_code == 404
    assert gebiete["Friedrichshain-Kreuzberg"] == ["Friedrichshain"]
    assert gebiete["Neukölln"] == ["Neukölln"]


def test_zufall_ohne_gebiet_findet_jede_adresse(adressen):
    zufall = random.Random(1)
    gezogen = {adressen.zufall(zufall)["strasse"] for _ in range(300)}
    assert gezogen == {"Karl-Marx-Straße", "Karl-Marx-Allee", "Werderstraße", "Stralauer Allee"}


def test_ein_ort_hinter_der_hausnummer_grenzt_ein(adressen):
    assert [t["ortsteil"] for t in adressen.suchen("Karl-Marx 92 neu")] == ["Neukölln", "Neukölln"]
    assert [t["strasse"] for t in adressen.suchen("Karl-Marx 92 fried")] == ["Karl-Marx-Allee"]
    assert [t["strasse"] for t in adressen.suchen("Karl-Marx 92 friedrichshain-kreuz")] == [
        "Karl-Marx-Allee"
    ]
    assert adressen.suchen("Karl-Marx 92 spandau") == []


def test_ein_ort_ohne_hausnummer_hinter_komma_oder_als_letztes_wort(adressen):
    assert [t["strasse"] for t in adressen.suchen("Karl-Marx, Friedrichshain")] == [
        "Karl-Marx-Allee"
    ]
    assert [t["strasse"] for t in adressen.suchen("Karl-Marx fried")] == ["Karl-Marx-Allee"]
    assert [t["plz"] for t in adressen.suchen("Karl-Marx-Str 92, 12043")] == ["12043", "12043"]
    assert [t["strasse"] for t in adressen.suchen("Stralauer Allee")] == ["Stralauer Allee"]


def test_tippfehler_finden_aehnliche_strassen_als_ungefaehr(adressen):
    treffer = adressen.suchen("Werdrestr 20")
    assert [(t["strasse"], t.get("ungefaehr")) for t in treffer] == [("Werderstraße", True)]
    assert all("ungefaehr" not in t for t in adressen.suchen("Werderstr 20"))
    assert [t["strasse"] for t in adressen.suchen("Kral-Marx-Allee")] == ["Karl-Marx-Allee"]


def test_wortanfaenge_finden_lange_strassennamen(tmp_path):
    cramm = merkmal(
        "Gottfried-von-Cramm-Weg", 5, None, "14193", "Grunewald", "Wilmersdorf", 13.27, 52.48
    )
    client, _ = wfs_mit([[*MERKMALE, cramm]])
    adressen = Adressen(tmp_path / "adressen.sqlite")
    adressen.laden(client)
    assert [t["strasse"] for t in adressen.suchen("Gott v Cra")] == ["Gottfried-von-Cramm-Weg"]
    assert [t["hausnummer"] for t in adressen.suchen("gott von cramm 5")] == ["5"]
    assert [t["strasse"] for t in adressen.suchen("Karl Allee")] == ["Karl-Marx-Allee"]
    assert "ungefaehr" not in adressen.suchen("Gott v Cra")[0]
    assert adressen.suchen("Cra Gott") == []


def test_die_naechste_tuer_liegt_im_umkreis(adressen):
    assert adressen.naechste(52.4793, 13.4386)["beschriftung"].startswith("Karl-Marx-Straße 92")
    assert adressen.naechste(52.5663, 13.2125)["strasse"] == "Werderstraße"
    assert adressen.naechste(52.40, 13.10) is None
