import json

import pytest
from fastapi.testclient import TestClient

import anleitungen
from einstellungen import einstellungen
from main import anwendung_bauen


def katalog(tmp_path, *eintraege):
    (tmp_path / "a.json").write_text(json.dumps({"anleitungen": list(eintraege)}))
    return tmp_path


def eintrag(id_="x", **felder):
    return {
        "id": id_,
        "titel": "T",
        "saetze": ["S"],
        "wenn": [{"fachrichtung": "rd"}],
        "quelle": "Q",
        **felder,
    }


def test_der_mitgelieferte_katalog_passt_zum_graphen(graph):
    geladen = anleitungen.laden(einstellungen().anleitungen_verzeichnis, graph)
    ids = {a.id for a in geladen}
    assert {"brand.wohnung.bleiben", "th.tier", "rd.seitenlage"} <= ids
    assert all(a.saetze and a.quelle for a in geladen)


@pytest.mark.parametrize(
    ("felder", "meldung"),
    [
        ({"wenn": [{"fachrichtung": "xx"}]}, "Fachrichtung xx"),
        ({"wenn": [{"protokolle": ["rd.99"]}]}, "Protokoll rd.99"),
        (
            {"wenn": [{"antworten": [{"knoten": "rd.atmung", "antwort": "x"}]}]},
            "Antwort x an rd.atmung",
        ),
        ({"wenn": []}, "ohne Bedingung"),
        ({"schliesstAus": ["y"]}, "schließt y aus"),
        ({"schliesstAus": ["x"]}, "schließt sich selbst aus"),
        ({"wenn": [{}]}, "ohne Bedingung"),
        ({"wenn": [{"kategorien": ["XYZ"]}]}, "keine Kategorie beginnt mit XYZ"),
        (
            {"wenn": [{"fachrichtung": "rd", "nicht": [{"knoten": "rd.atmung", "antwort": "y"}]}]},
            "Antwort y an rd.atmung",
        ),
    ],
)
def test_fehler_im_katalog_werden_genannt(tmp_path, graph, felder, meldung):
    with pytest.raises(ValueError, match=meldung):
        anleitungen.laden(katalog(tmp_path, eintrag(**felder)), graph)


def test_doppelte_ids_werden_genannt(tmp_path, graph):
    with pytest.raises(ValueError, match="x: gibt es doppelt"):
        anleitungen.laden(katalog(tmp_path, eintrag(), eintrag()), graph)


def test_der_katalog_kommt_mit_dem_graphen():
    with TestClient(anwendung_bauen()) as client:
        buendel = client.get("/api/abfrage").json()
    bleiben = next(a for a in buendel["anleitungen"] if a["id"] == "brand.wohnung.bleiben")
    assert bleiben["schliesstAus"] == ["brand.wohnung.verlassen"]
    assert bleiben["wenn"][0]["antworten"][0]["antwort"] == "weg-verraucht"
    assert bleiben["pflicht"] is True


def test_eine_kaputte_datei_wird_genannt(tmp_path, graph):
    (tmp_path / "kaputt.json").write_text(json.dumps({"anleitungen": [{"id": "x"}]}))
    with pytest.raises(ValueError, match="kaputt.json"):
        anleitungen.laden(tmp_path, graph)


def test_der_rettungsdienst_endet_mit_dem_hinweis_erneut_anzurufen():
    with TestClient(anwendung_bauen()) as client:
        buendel = client.get("/api/abfrage").json()
    hinweis = next(a for a in buendel["anleitungen"] if a["id"] == "rd.erneut-anrufen")
    assert hinweis["pflicht"] is True
    assert hinweis["auchOhneVorOrt"] is True
    assert hinweis["wenn"] == [
        {
            "fachrichtung": "rd",
            "nicht": [{"knoten": "rd.atmung", "antwort": "atmet-nicht"}],
            "nichtKategorien": ["RD1NC REA", "RD1NC NNAD"],
        }
    ]


def test_unbekannte_ausgeschlossene_kategorien_fallen_auf(tmp_path, graph):
    eintrag = {
        "id": "x",
        "titel": "X",
        "saetze": ["S"],
        "wenn": [{"fachrichtung": "rd", "nichtKategorien": ["GIBTSNICHT"]}],
        "quelle": "Q",
    }
    (tmp_path / "a.json").write_text(json.dumps({"anleitungen": [eintrag]}), "utf-8")
    with pytest.raises(ValueError, match="keine Kategorie beginnt mit GIBTSNICHT"):
        anleitungen.laden(tmp_path, graph)
