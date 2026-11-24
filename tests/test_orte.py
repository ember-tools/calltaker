import gzip
import json

import pytest
from fastapi.testclient import TestClient

from main import anwendung_bauen
from orte import Orte, suchform

ORTE = [
    ["Vivantes Klinikum - Neukölln", "Krankenhaus", "Buckow", 52.43, 13.43],
    ["Rathaus Neukölln", "Rathaus", "Neukölln", 52.48, 13.43],
    ["Rathaus Neukölln", "Bahnhof", "Neukölln", 52.48, 13.44],
    ["U Rathaus Neukölln / Alfred-Scholz-Platz", "Bushaltestelle", "Neukölln", 52.48, 13.43],
    ["Tempelhofer Feld", "Erholungsfläche", "Tempelhof", 52.47, 13.40],
]


@pytest.fixture
def verzeichnis(tmp_path):
    (tmp_path / "orte.json.gz").write_bytes(gzip.compress(json.dumps(ORTE).encode()))
    (tmp_path / "meta.json").write_text(json.dumps({"stand": "2026-11-22"}))
    return tmp_path


def test_jedes_wort_zaehlt_satzzeichen_nicht(verzeichnis):
    treffer = Orte(verzeichnis).suchen("klinikum neukölln")
    assert [t["name"] for t in treffer] == ["Vivantes Klinikum - Neukölln"]
    assert treffer[0]["beschriftung"] == "Vivantes Klinikum - Neukölln (Krankenhaus), Buckow"
    assert treffer[0]["breite"] == 52.43


def test_was_mit_dem_text_beginnt_kommt_zuerst(verzeichnis):
    namen = [(t["name"], t["art"]) for t in Orte(verzeichnis).suchen("rathaus neuk")]
    assert sorted(namen[:2]) == [("Rathaus Neukölln", "Bahnhof"), ("Rathaus Neukölln", "Rathaus")]
    assert namen[2][0].startswith("U Rathaus")


def test_kurze_texte_und_eine_fehlende_datei_finden_nichts(verzeichnis, tmp_path_factory):
    assert Orte(verzeichnis).suchen("Te") == []
    assert Orte(tmp_path_factory.mktemp("leer")).suchen("Tempelhof") == []
    assert suchform("  Alfred-Scholz-Platz / U ") == "alfred scholz platz u"


def test_die_suchroute_liefert_orte(verzeichnis, monkeypatch):
    from einstellungen import einstellungen

    monkeypatch.setattr(einstellungen(), "orte_verzeichnis", verzeichnis)
    with TestClient(anwendung_bauen()) as client:
        antwort = client.get("/api/orte/suche", params={"q": "tempelhofer"})
    assert [o["name"] for o in antwort.json()] == ["Tempelhofer Feld"]


def test_die_mitgelieferten_orte_sind_da():
    from einstellungen import einstellungen

    orte = Orte(einstellungen().orte_verzeichnis)
    assert len(orte.orte) > 10000
    assert orte.meta["lizenz"].startswith("Open Database License")
    assert any(o["art"] == "Bahnhof" for o in orte.suchen("Alexanderplatz"))


def test_ein_lfs_zeiger_laesst_den_server_ohne_orte_starten(tmp_path, caplog):
    (tmp_path / "orte.json.gz").write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 1\n"
    )
    assert Orte(tmp_path).suchen("Tempelhofer") == []
    assert "git lfs pull" in caplog.text


def test_der_ortsteil_grenzt_ketten_ein(tmp_path):
    orte = [
        ["Lidl", "Supermarkt", "Buckow", 52.4, 13.4],
        ["Lidl", "Supermarkt", "Neukölln", 52.48, 13.43],
        ["Neuköllner Lidl-Markt", "Supermarkt", "Britz", 52.45, 13.43],
    ]
    (tmp_path / "orte.json.gz").write_bytes(gzip.compress(json.dumps(orte).encode()))
    treffer = Orte(tmp_path).suchen("Lidl Neukölln")
    assert [(t["name"], t["ortsteil"]) for t in treffer] == [
        ("Neuköllner Lidl-Markt", "Britz"),
        ("Lidl", "Neukölln"),
    ]


ORTSTEILE = {
    "Adlershof",
    "Alt-Hohenschönhausen",
    "Alt-Treptow",
    "Altglienicke",
    "Baumschulenweg",
    "Biesdorf",
    "Blankenburg",
    "Blankenfelde",
    "Bohnsdorf",
    "Borsigwalde",
    "Britz",
    "Buch",
    "Buckow",
    "Charlottenburg",
    "Charlottenburg-Nord",
    "Dahlem",
    "Falkenberg",
    "Falkenhagener Feld",
    "Fennpfuhl",
    "Französisch Buchholz",
    "Friedenau",
    "Friedrichsfelde",
    "Friedrichshagen",
    "Friedrichshain",
    "Frohnau",
    "Gatow",
    "Gesundbrunnen",
    "Gropiusstadt",
    "Grunewald",
    "Grünau",
    "Hakenfelde",
    "Halensee",
    "Hansaviertel",
    "Haselhorst",
    "Heiligensee",
    "Heinersdorf",
    "Hellersdorf",
    "Hermsdorf",
    "Johannisthal",
    "Karlshorst",
    "Karow",
    "Kaulsdorf",
    "Kladow",
    "Konradshöhe",
    "Kreuzberg",
    "Köpenick",
    "Lankwitz",
    "Lichtenberg",
    "Lichtenrade",
    "Lichterfelde",
    "Lübars",
    "Mahlsdorf",
    "Malchow",
    "Mariendorf",
    "Marienfelde",
    "Marzahn",
    "Mitte",
    "Moabit",
    "Märkisches Viertel",
    "Müggelheim",
    "Neu-Hohenschönhausen",
    "Neukölln",
    "Niederschöneweide",
    "Niederschönhausen",
    "Nikolassee",
    "Oberschöneweide",
    "Pankow",
    "Plänterwald",
    "Prenzlauer Berg",
    "Rahnsdorf",
    "Reinickendorf",
    "Rosenthal",
    "Rudow",
    "Rummelsburg",
    "Schlachtensee",
    "Schmargendorf",
    "Schmöckwitz",
    "Schöneberg",
    "Siemensstadt",
    "Spandau",
    "Staaken",
    "Stadtrandsiedlung Malchow",
    "Steglitz",
    "Tegel",
    "Tempelhof",
    "Tiergarten",
    "Waidmannslust",
    "Wannsee",
    "Wartenberg",
    "Wedding",
    "Weißensee",
    "Westend",
    "Wilhelmsruh",
    "Wilhelmstadt",
    "Wilmersdorf",
    "Wittenau",
    "Zehlendorf",
}


def test_die_ortsteile_der_orte_sind_die_des_adressverzeichnisses():
    from einstellungen import einstellungen

    assert {ort.ortsteil for ort in Orte(einstellungen().orte_verzeichnis).orte} == ORTSTEILE


def test_zufaellige_orte_nach_art_und_ortsteil(verzeichnis):
    import random

    orte = Orte(verzeichnis)
    zufall = random.Random(1)
    assert {orte.zufall(zufall, arten={"Rathaus"})["art"] for _ in range(20)} == {"Rathaus"}
    assert orte.zufall(zufall, "Buckow", {"Rathaus"}) is None


def test_der_umkreis_liefert_nahe_orte_naechste_zuerst(verzeichnis):
    orte = Orte(verzeichnis)
    alle = [(o.name, o.breite, o.laenge) for o in orte.orte]
    name, breite, laenge = alle[0]
    nahe = orte.umkreis(breite, laenge, 50)
    assert nahe[0]["name"] == name
    assert all(o["name"] != name for o in orte.umkreis(breite + 0.1, laenge, 50))
