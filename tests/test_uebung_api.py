import time

import pytest
from fastapi.testclient import TestClient

import uebung
from einstellungen import einstellungen
from main import anwendung_bauen


@pytest.fixture
def client():
    with TestClient(anwendung_bauen()) as client:
        yield client


@pytest.fixture
def codes(client):
    antwort = client.post("/api/uebung")
    assert antwort.status_code == 201
    return antwort.json()


def absicht(client, code, **daten):
    return client.post(f"/api/uebung/{code}/absicht", json=daten)


def test_ein_code_nennt_seine_rolle(client, codes):
    assert client.get(f"/api/uebung/{codes['ausbilderCode']}").json() == {"rolle": "ausbilder"}
    assert client.get(f"/api/uebung/{codes['traineeCode']}").json() == {"rolle": "trainee"}
    unbekannt = client.get("/api/uebung/A-XXXXXX")
    assert unbekannt.status_code == 404
    assert unbekannt.json() == {"detail": "Diesen Code gibt es nicht."}


def test_ohne_aenderung_antwortet_die_abfrage_leer(client, codes):
    code = codes["traineeCode"]
    erste = client.get(f"/api/uebung/{code}/zustand").json()
    assert erste["zustand"]["verbunden"]["trainee"] is True
    leer = client.get(f"/api/uebung/{code}/zustand", params={"version": erste["version"]})
    assert leer.status_code == 204
    assert leer.content == b""


def test_die_andere_seite_sieht_wer_verbunden_ist(client, codes):
    client.get(f"/api/uebung/{codes['traineeCode']}/zustand")
    ausbilder = client.get(f"/api/uebung/{codes['ausbilderCode']}/zustand").json()["zustand"]
    assert ausbilder["verbunden"] == {"ausbilder": True, "trainee": True}


def test_der_ausbilder_pflegt_den_pool(client, codes, szenario_daten):
    code = codes["ausbilderCode"]
    hinzu = absicht(client, code, art="pool.hinzufuegen", szenario=szenario_daten)
    assert hinzu.status_code == 200
    szenario_id = hinzu.json()["ergebnis"]["szenarioId"]
    assert hinzu.json()["ergebnis"]["befunde"] == []
    absicht(client, code, art="pool.hinzufuegen", szenario={**szenario_daten, "titel": "Zweites"})
    absicht(client, code, art="pool.verschieben", szenarioId=szenario_id, ziel=1)
    zustand = client.get(f"/api/uebung/{code}/zustand").json()
    assert [s["titel"] for s in zustand["zustand"]["pool"]] == ["Zweites", szenario_daten["titel"]]
    assert absicht(client, code, art="pool.entfernen", szenarioId=szenario_id).status_code == 200
    assert absicht(client, code, art="pool.entfernen", szenarioId=szenario_id).status_code == 404


def test_eine_absicht_erhoeht_die_version(client, codes, szenario_daten):
    code = codes["ausbilderCode"]
    vorher = client.get(f"/api/uebung/{code}/zustand").json()["version"]
    nachher = absicht(client, code, art="pool.hinzufuegen", szenario=szenario_daten).json()[
        "version"
    ]
    assert nachher > vorher
    assert client.get(f"/api/uebung/{code}/zustand", params={"version": vorher}).status_code == 200


def test_der_trainee_darf_den_pool_nicht_aendern(client, codes, szenario_daten):
    antwort = absicht(client, codes["traineeCode"], art="pool.hinzufuegen", szenario=szenario_daten)
    assert antwort.status_code == 403
    assert antwort.json() == {"detail": "Das darf diese Rolle nicht."}
    pool = client.get(f"/api/uebung/{codes['traineeCode']}/pool")
    assert pool.status_code == 403


def test_ungueltiges_wird_auf_deutsch_abgelehnt(client, codes, szenario_daten):
    code = codes["ausbilderCode"]
    unbekannt = absicht(client, code, art="zaubern")
    assert unbekannt.status_code == 400
    assert unbekannt.json()["detail"] == "Die Absicht zaubern gibt es nicht."
    kaputt = absicht(client, code, art="pool.hinzufuegen", szenario={**szenario_daten, "titel": 3})
    assert kaputt.status_code == 422
    assert kaputt.json()["detail"] == "titel: muss ein Text sein"
    datei = absicht(client, code, art="pool.importieren", datei={"format": "x"})
    assert datei.status_code == 422
    assert "format: muss 'calltaker-pool' sein" in datei.json()["detail"]


def test_export_und_import_ueber_die_uebung(client, codes, szenario_daten):
    code = codes["ausbilderCode"]
    absicht(client, code, art="pool.hinzufuegen", szenario=szenario_daten)
    datei = client.get(f"/api/uebung/{code}/pool")
    assert datei.headers["content-disposition"].startswith("attachment")
    neu = client.post("/api/uebung").json()["ausbilderCode"]
    importiert = absicht(client, neu, art="pool.importieren", datei=datei.json(), modus="ersetzen")
    assert importiert.status_code == 200
    pool = client.get(f"/api/uebung/{neu}/zustand").json()["zustand"]["pool"]
    assert [s["titel"] for s in pool] == [szenario_daten["titel"]]


def test_der_ausbilder_sieht_was_der_trainee_tippt(client, codes):
    spiegel = absicht(client, codes["traineeCode"], art="spiegeln", felder={"strasse": "Karl-Ma"})
    assert spiegel.status_code == 200
    zustand = client.get(f"/api/uebung/{codes['ausbilderCode']}/zustand").json()["zustand"]
    assert zustand["spiegel"] == {"strasse": "Karl-Ma"}
    zu_viel = absicht(client, codes["traineeCode"], art="spiegeln", felder={"x": "a" * 5000})
    assert zu_viel.status_code == 413
    assert absicht(client, codes["ausbilderCode"], art="spiegeln", felder={}).status_code == 403


def version_von(client, code):
    return client.get(f"/api/uebung/{code}/zustand").json()["version"]


def test_der_ausbilder_ersetzt_ein_szenario(client, codes, szenario_daten):
    code = codes["ausbilderCode"]
    szenario_id = absicht(client, code, art="pool.hinzufuegen", szenario=szenario_daten).json()[
        "ergebnis"
    ]["szenarioId"]
    neu = {**szenario_daten, "id": szenario_id, "titel": "Neu"}
    assert absicht(client, code, art="pool.ersetzen", szenario=neu).status_code == 200
    assert client.get(f"/api/uebung/{code}/zustand").json()["zustand"]["pool"][0]["titel"] == "Neu"
    fremd = absicht(client, code, art="pool.ersetzen", szenario={**neu, "id": "gibtesnicht"})
    assert fremd.status_code == 404
    assert fremd.json()["detail"] == "Dieses Szenario gibt es nicht."


def test_verschieben_braucht_ein_ziel(client, codes, szenario_daten):
    code = codes["ausbilderCode"]
    szenario_id = absicht(client, code, art="pool.hinzufuegen", szenario=szenario_daten).json()[
        "ergebnis"
    ]["szenarioId"]
    antwort = absicht(client, code, art="pool.verschieben", szenarioId=szenario_id)
    assert antwort.status_code == 400
    assert antwort.json()["detail"] == "Das Ziel der Verschiebung fehlt."


def test_abgelehnte_absichten_lassen_die_version_stehen(client, codes, szenario_daten):
    code = codes["ausbilderCode"]
    vorher = version_von(client, code)
    absicht(client, code, art="pool.entfernen", szenarioId="gibtesnicht")
    absicht(client, codes["traineeCode"], art="pool.hinzufuegen", szenario=szenario_daten)
    assert version_von(client, code) == vorher


def test_ein_unveraenderter_spiegel_laesst_die_version_stehen(client, codes):
    absicht(client, codes["traineeCode"], art="spiegeln", felder={"name": "A"})
    vorher = version_von(client, codes["ausbilderCode"])
    absicht(client, codes["traineeCode"], art="spiegeln", felder={"name": "A"})
    assert version_von(client, codes["ausbilderCode"]) == vorher


def test_eine_volle_verwaltung_antwortet_503(monkeypatch):
    monkeypatch.setattr(einstellungen(), "uebungen_hoechstens", 1)
    with TestClient(anwendung_bauen()) as client:
        assert client.post("/api/uebung").status_code == 201
        voll = client.post("/api/uebung")
    assert voll.status_code == 503
    assert voll.json()["detail"] == "Gerade laufen zu viele Übungen."


def test_zu_grosse_anfragen_werden_abgelehnt(client, codes):
    riesig = {"art": "pool.importieren", "datei": {"x": "a" * (3 * 1024 * 1024)}}
    antwort = client.post(f"/api/uebung/{codes['ausbilderCode']}/absicht", json=riesig)
    assert antwort.status_code == 413
    assert antwort.json() == {"detail": "Die Anfrage ist zu groß."}


def test_zu_grosse_anfragen_ohne_laengenangabe_werden_abgelehnt(client, codes):
    def stuecke():
        yield b'{"art": "pool.importieren", "datei": "'
        for _ in range(40):
            yield b"a" * (100 * 1024)
        yield b'"}'

    antwort = client.post(
        f"/api/uebung/{codes['ausbilderCode']}/absicht",
        content=stuecke(),
        headers={"Content-Type": "application/json"},
    )
    assert antwort.status_code == 413
    assert antwort.json() == {"detail": "Die Anfrage ist zu groß."}


def test_der_server_merkt_ohne_abfrage_dass_jemand_fehlt(monkeypatch):
    monkeypatch.setattr(uebung, "ONLINE_FRIST", 0.2)
    with TestClient(anwendung_bauen()) as client:
        codes = client.post("/api/uebung").json()
        client.get(f"/api/uebung/{codes['traineeCode']}/zustand")
        uebung_ = client.app.state.uebungen.finden(codes["traineeCode"])[0]
        assert uebung_.verbunden[uebung.Rolle.TRAINEE]
        time.sleep(1.5)
        assert not uebung_.verbunden[uebung.Rolle.TRAINEE]
