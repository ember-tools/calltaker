import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from anruf import Anruf
from eintraege import (
    Abfrageeintrag,
    Eintraege,
    Reanimationseintrag,
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


def test_gegebene_anleitungen_werden_einmal_gestempelt():
    erste = uebernehmen(
        Eintraege(), Eintraege.model_validate({"anleitung": {"gegeben": ["a"]}}), 10.0
    )
    zweite = uebernehmen(
        erste, Eintraege.model_validate({"anleitung": {"gegeben": ["a", "b"]}}), 20.0
    )
    dritte = uebernehmen(zweite, Eintraege(), 30.0)
    assert zweite.zeiten.anleitungen == {"a": 10.0, "b": 20.0}
    assert dritte.zeiten.anleitungen == {"a": 10.0, "b": 20.0}
    assert Eintraege.model_validate({"zeiten": {"anleitungen": {"x": 1}}}).zeiten.anleitungen == {
        "x": 1
    }


def test_anleitungen_sind_begrenzt():
    with pytest.raises(ValidationError):
        Eintraege.model_validate({"anleitung": {"gegeben": ["x" * 201]}})
    with pytest.raises(ValidationError):
        Eintraege.model_validate({"anleitung": {"gegeben": [str(i) for i in range(101)]}})
    bisher = Eintraege()
    for runde in range(3):
        neu = Eintraege.model_validate(
            {"anleitung": {"gegeben": [f"{runde}-{i}" for i in range(100)]}}
        )
        bisher = uebernehmen(bisher, neu, float(runde))
    assert len(bisher.zeiten.anleitungen) == 100


def test_der_erste_start_der_reanimation_wird_gestempelt():
    laeuft = Eintraege.model_validate({"reanimation": {"laeuft": True, "takt": 110}})
    erste = uebernehmen(Eintraege(), laeuft, 10.0)
    angehalten = uebernehmen(erste, Eintraege(), 20.0)
    wieder = uebernehmen(angehalten, laeuft, 30.0)
    assert (erste.zeiten.reanimation, wieder.zeiten.reanimation) == (10.0, 10.0)
    for takt in (99, 121):
        with pytest.raises(ValidationError):
            Eintraege.model_validate({"reanimation": {"takt": takt}})


def test_die_uebergabe_wird_einmal_gestempelt_und_ihr_stand_bleibt():
    vorher = Eintraege.model_validate({"hinweise": "erst", "betroffener": "A"})
    uebergabe = Eintraege.model_validate(
        {"hinweise": "erst", "betroffener": "A", "uebergabe": True}
    )
    erste = uebernehmen(uebernehmen(Eintraege(), vorher, 5.0), uebergabe, 10.0)
    gefaelscht = Eintraege.model_validate(
        {
            "hinweise": "nachgetragen",
            "uebergabe": False,
            "uebergeben": {
                "ort": {},
                "anrufer": {},
                "betroffener": "X",
                "abfrage": {},
                "hinweise": "x",
            },
        }
    )
    spaeter = uebernehmen(erste, gefaelscht, 20.0)
    assert erste.zeiten.uebergabe == 10.0
    assert spaeter.zeiten.uebergabe == 10.0
    assert spaeter.uebergabe is True
    assert spaeter.uebergeben.hinweise == "erst"
    assert spaeter.uebergeben.betroffener == "A"
    assert spaeter.hinweise == "nachgetragen"
    assert uebernehmen(Eintraege(), vorher, 5.0).uebergeben is None


def test_die_antwort_bringt_zeiten_und_uebergabestand(gespraech):
    client, _, t, anruf_id = gespraech
    vorher = eintragen(client, t, anruf_id, {"hinweise": "Tür offen"}).json()["ergebnis"]
    assert vorher["uebergeben"] is None
    assert "uebergabe" not in vorher["zeiten"]
    danach = eintragen(client, t, anruf_id, {"hinweise": "Tür offen", "uebergabe": True}).json()
    assert danach["ergebnis"]["zeiten"]["uebergabe"] > 0
    assert danach["ergebnis"]["uebergeben"]["hinweise"] == "Tür offen"


def test_bei_einer_reanimation_treffen_die_kraefte_nach_der_anfahrt_ein(gespraech):
    client, a, t, anruf_id = gespraech
    eintragen(client, t, anruf_id, {"hinweise": "x"})
    assert (
        "eintreffenUm" not in client.get(f"/api/uebung/{t}/zustand").json()["zustand"]["anrufe"][0]
    )
    eintragen(client, t, anruf_id, {"reanimation": {"laeuft": True, "takt": 100}})
    anruf = client.get(f"/api/uebung/{a}/zustand").json()["zustand"]["anrufe"][0]
    start = anruf["eintraege"]["zeiten"]["reanimation"]
    assert 60 <= anruf["eintreffenUm"] - start <= 180
    eintragen(
        client, t, anruf_id, {"reanimation": {"laeuft": True, "takt": 100}, "uebergabe": True}
    )
    anruf = client.get(f"/api/uebung/{a}/zustand").json()["zustand"]["anrufe"][0]
    uebergabe = anruf["eintraege"]["zeiten"]["uebergabe"]
    assert 60 <= anruf["eintreffenUm"] - uebergabe <= 180
    sicht = client.get(f"/api/uebung/{t}/zustand").json()["zustand"]["anrufe"][0]
    assert sicht["eintreffenUm"] == anruf["eintreffenUm"]


def test_der_ausbilder_laesst_die_kraefte_vorzeitig_eintreffen(gespraech):
    client, a, t, anruf_id = gespraech
    eintragen(client, t, anruf_id, {"reanimation": {"laeuft": True, "takt": 100}})
    vorher = client.get(f"/api/uebung/{a}/zustand").json()["zustand"]["anrufe"][0]["eintreffenUm"]
    absicht = {"art": "anruf.eintreffen", "anrufId": anruf_id}
    assert client.post(f"/api/uebung/{t}/absicht", json=absicht).status_code == 403
    assert client.post(f"/api/uebung/{a}/absicht", json=absicht).status_code == 200
    jetzt = client.get(f"/api/uebung/{a}/zustand").json()["zustand"]["anrufe"][0]["eintreffenUm"]
    assert jetzt < vorher
    falsch = {"art": "anruf.eintreffen", "anrufId": "x"}
    assert client.post(f"/api/uebung/{a}/absicht", json=falsch).status_code == 409


def test_ohne_reanimation_treffen_keine_kraefte_ein(gespraech):
    client, a, _, anruf_id = gespraech
    absicht = {"art": "anruf.eintreffen", "anrufId": anruf_id}
    antwort = client.post(f"/api/uebung/{a}/absicht", json=absicht)
    assert antwort.status_code == 409
    assert antwort.json()["detail"] == "Hier läuft keine Reanimation."


def test_eingetroffene_kraefte_bleiben_trotz_spaeter_uebergabe(szenario_daten):
    anruf = Anruf.model_validate({"szenario": szenario_daten, "klingeltSeit": 0, "anfahrt": 60.0})
    anruf.eintraege.zeiten.reanimation = 100.0
    assert anruf.eintreffen_um == 160.0
    anruf.eintraege.zeiten.uebergabe = 190.0
    assert anruf.eintreffen_um == 160.0
    anruf.eintraege.zeiten.uebergabe = 130.0
    assert anruf.eintreffen_um == 190.0


def test_die_reanimation_merkt_sich_die_gewaehlte_altersgruppe():
    assert Reanimationseintrag.model_validate({"gruppe": "saeugling"}).gruppe == "saeugling"
    assert Reanimationseintrag().gruppe is None
    with pytest.raises(ValidationError):
        Reanimationseintrag.model_validate({"gruppe": "greis"})
