import pytest
from fastapi.testclient import TestClient

from eintraege import (
    Abfrageeintrag,
    Eintraege,
    Schritteintrag,
    uebernehmen,
)
from main import anwendung_bauen


def pfad_zu(graph, protokoll="rd.17"):
    endpunkt = next(e for e in graph.endpunkte if e.protokoll == protokoll)
    return endpunkt, [Schritteintrag(knoten=s.knoten, antwort=s.antwort) for s in endpunkt.pfad]


def test_die_zeiten_stempelt_der_server_einmal():
    leer = Eintraege()
    mit_ort = Eintraege.model_validate({"ort": {"koordinaten": [52.5, 13.4]}})
    erste = uebernehmen(leer, mit_ort, 100.0)
    assert erste.zeiten.adresse == 100.0
    assert erste.zeiten.code is None
    mit_code = mit_ort.model_copy(update={"abfrage": Abfrageeintrag(code_erreicht=True)})
    zweite = uebernehmen(erste, mit_code, 130.0)
    assert (zweite.zeiten.adresse, zweite.zeiten.code) == (100.0, 130.0)
    falsch = Eintraege.model_validate({"zeiten": {"adresse": 1, "code": 1}})
    assert uebernehmen(zweite, falsch, 200.0).zeiten == zweite.zeiten


@pytest.fixture
def gespraech(szenario_daten):
    with TestClient(anwendung_bauen()) as client:
        codes = client.post("/api/uebung").json()
        a, t = codes["ausbilderCode"], codes["traineeCode"]
        client.post(
            f"/api/uebung/{a}/absicht", json={"art": "pool.hinzufuegen", "szenario": szenario_daten}
        )
        szenario_id = client.get(f"/api/uebung/{a}/zustand").json()["zustand"]["pool"][0]["id"]
        client.post(f"/api/uebung/{t}/absicht", json={"art": "bereit"})
        anruf = client.post(
            f"/api/uebung/{a}/absicht", json={"art": "engine.sofort", "szenarioId": szenario_id}
        )
        anruf_id = anruf.json()["ergebnis"]["anrufId"]
        client.post(f"/api/uebung/{t}/absicht", json={"art": "annehmen", "anrufId": anruf_id})
        yield client, a, t, anruf_id


def eintragen(client, code, anruf_id, eintraege):
    return client.post(
        f"/api/uebung/{code}/absicht",
        json={"art": "eintragen", "anrufId": anruf_id, "eintraege": eintraege},
    )


def test_eintraege_erreichen_den_ausbilder(gespraech):
    client, a, t, anruf_id = gespraech
    antwort = eintragen(
        client, t, anruf_id, {"anrufer": {"name": "Ayşe", "rufnummerBestaetigt": True}}
    )
    assert antwort.status_code == 200
    anruf = client.get(f"/api/uebung/{a}/zustand").json()["zustand"]["anrufe"][0]
    assert anruf["eintraege"]["anrufer"] == {
        "name": "Ayşe",
        "rufnummerBestaetigt": True,
        "rueckrufnummer": "",
    }
    trainee = client.get(f"/api/uebung/{t}/zustand").json()["zustand"]["anrufe"][0]
    assert trainee["eintraege"]["anrufer"]["name"] == "Ayşe"


def test_unveraenderte_eintraege_lassen_die_version_stehen(gespraech):
    client, a, t, anruf_id = gespraech
    eintragen(client, t, anruf_id, {"hinweise": "Tür offen"})
    vorher = client.get(f"/api/uebung/{a}/zustand").json()["version"]
    eintragen(client, t, anruf_id, {"hinweise": "Tür offen"})
    assert client.get(f"/api/uebung/{a}/zustand").json()["version"] == vorher


def test_eintraege_brauchen_ein_laufendes_gespraech(gespraech):
    client, a, t, anruf_id = gespraech
    assert eintragen(client, t, "anderer", {}).status_code == 409
    assert eintragen(client, a, anruf_id, {}).status_code == 403
    ungueltig = eintragen(client, t, anruf_id, {"hinweise": "x" * 5000})
    assert ungueltig.status_code == 422
    ohne = client.post(f"/api/uebung/{t}/absicht", json={"art": "eintragen", "anrufId": anruf_id})
    assert ohne.status_code == 422
    assert ohne.json()["detail"] == "Die Einträge fehlen."
    client.post(f"/api/uebung/{t}/absicht", json={"art": "beenden"})
    vorbei = eintragen(client, t, anruf_id, {})
    assert vorbei.status_code == 409
    assert vorbei.json()["detail"] == "Es läuft kein Gespräch."
