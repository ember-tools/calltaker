import time

import pytest
from fastapi.testclient import TestClient

import uebung
from einstellungen import einstellungen
from main import anwendung_bauen
from rolle import Rolle


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
        assert uebung_.verbunden[Rolle.TRAINEE]
        time.sleep(1.5)
        assert not uebung_.verbunden[Rolle.TRAINEE]


def zustand_von(client, code):
    return client.get(f"/api/uebung/{code}/zustand").json()["zustand"]


def test_der_ablauf_eines_anrufs_ueber_die_absichten(client, codes, szenario_daten):
    a, t = codes["ausbilderCode"], codes["traineeCode"]
    absicht(client, a, art="pool.hinzufuegen", szenario=szenario_daten)
    szenario_id = zustand_von(client, a)["pool"][0]["id"]
    assert absicht(client, t, art="bereit").status_code == 200
    assert zustand_von(client, t)["engine"]["gestartet"] is True
    anruf_id = absicht(client, a, art="engine.sofort", szenarioId=szenario_id).json()["ergebnis"][
        "anrufId"
    ]
    trainee = zustand_von(client, t)
    assert trainee["anrufe"][0]["zustand"] == "wartet"
    assert "szenario" not in trainee["anrufe"][0]
    assert absicht(client, t, art="annehmen", anrufId=anruf_id).status_code == 200
    doppelt = absicht(client, t, art="annehmen", anrufId=anruf_id)
    assert doppelt.status_code == 409
    assert doppelt.json()["detail"] == "Es läuft schon ein Gespräch."
    assert absicht(client, t, art="beenden").status_code == 200
    assert zustand_von(client, t)["anrufe"][0]["szenario"]["titel"] == szenario_daten["titel"]


def test_der_ausbilder_steuert_die_engine(client, codes, szenario_daten):
    a, t = codes["ausbilderCode"], codes["traineeCode"]
    absicht(client, a, art="pool.hinzufuegen", szenario=szenario_daten)
    absicht(client, t, art="bereit")
    assert absicht(client, a, art="engine.pausieren", an=True).status_code == 200
    assert zustand_von(client, a)["engine"]["manuellPausiert"] is True
    assert absicht(client, a, art="engine.pausieren").status_code == 400
    szenario_id = zustand_von(client, a)["pool"][0]["id"]
    anruf_id = absicht(client, a, art="engine.sofort", szenarioId=szenario_id).json()["ergebnis"][
        "anrufId"
    ]
    assert absicht(client, a, art="anruf.auflegen", anrufId=anruf_id).status_code == 200
    assert absicht(client, a, art="anruf.auflegen", anrufId=anruf_id).status_code == 404
    neu = absicht(client, a, art="engine.parameter", parameter={"maxSchlange": 3, "geduldMin": 120})
    assert neu.status_code == 200
    absicht(client, a, art="engine.parameter", parameter={"basisAbstand": 30})
    parameter = zustand_von(client, a)["engine"]["parameter"]
    assert (parameter["maxSchlange"], parameter["geduldMin"], parameter["basisAbstand"]) == (
        3,
        120,
        30,
    )
    falsch = absicht(
        client, a, art="engine.parameter", parameter={"geduldMin": 500, "geduldMax": 100}
    )
    assert falsch.status_code == 422
    assert falsch.json()["detail"] == "Die Geduld braucht min ≤ max."


def test_rollen_steuern_nur_ihren_teil(client, codes):
    a, t = codes["ausbilderCode"], codes["traineeCode"]
    assert absicht(client, t, art="engine.pausieren", an=True).status_code == 403
    assert absicht(client, a, art="bereit").status_code == 403
    assert absicht(client, a, art="annehmen", anrufId="x").status_code == 403
    engine = zustand_von(client, t)["engine"]
    assert not {"parameter", "naechstesKlingeln", "manuellPausiert"} & set(engine)


def test_eine_fehlerhafte_uebung_haelt_die_anderen_nicht_auf(monkeypatch, caplog):
    monkeypatch.setattr(uebung, "ONLINE_FRIST", 0.2)
    with TestClient(anwendung_bauen()) as client:
        kaputt = client.post("/api/uebung").json()
        heil = client.post("/api/uebung").json()
        client.get(f"/api/uebung/{kaputt['traineeCode']}/zustand")
        client.get(f"/api/uebung/{heil['traineeCode']}/zustand")
        alle = client.app.state.uebungen
        kaputte = alle.finden(kaputt["traineeCode"])[0]

        def fehler():
            raise RuntimeError("kaputt")

        monkeypatch.setattr(kaputte.engine, "takt", fehler)
        time.sleep(1.5)
        assert not alle.finden(heil["traineeCode"])[0].verbunden[Rolle.TRAINEE]
    assert kaputte.kennung in caplog.text
    assert kaputt["ausbilderCode"] not in caplog.text


def test_der_ausbilder_sieht_die_befunde_seines_pools(client, codes, szenario_daten):
    code = codes["ausbilderCode"]
    kaputt = {
        **szenario_daten,
        "antworten": {**szenario_daten["antworten"], "gibt.es.nicht": {"antwort": "x"}},
    }
    hinzu = absicht(client, code, art="pool.hinzufuegen", szenario=kaputt)
    szenario_id = hinzu.json()["ergebnis"]["szenarioId"]
    zustand = client.get(f"/api/uebung/{code}/zustand").json()["zustand"]
    assert [b["knoten"] for b in zustand["poolBefunde"][szenario_id]] == ["gibt.es.nicht"]
    absicht(client, code, art="pool.ersetzen", szenario={**szenario_daten, "id": szenario_id})
    assert client.get(f"/api/uebung/{code}/zustand").json()["zustand"]["poolBefunde"] == {}


def test_nur_aenderungen_des_ausbilders_zaehlen_fuer_den_pool_stand(client, codes, szenario_daten):
    code = codes["ausbilderCode"]

    def stand():
        return client.get(f"/api/uebung/{code}/zustand").json()["zustand"]["poolStand"]

    vorher = stand()
    absicht(client, code, art="pool.hinzufuegen", szenario=szenario_daten)
    assert stand() == vorher + 1
    uebung, _ = client.app.state.uebungen.finden(code)
    uebung.pool_entnehmen()
    assert stand() == vorher + 1


def test_der_ausbilder_generiert_szenarien(client, codes):
    code = codes["ausbilderCode"]
    hinzu = absicht(client, code, art="pool.generieren", anzahl=3)
    assert hinzu.status_code == 200
    assert len(hinzu.json()["ergebnis"]["szenarioIds"]) == 3
    zustand = client.get(f"/api/uebung/{code}/zustand").json()["zustand"]
    assert [s["herkunft"] for s in zustand["pool"]] == ["generiert"] * 3
    assert zustand["poolStand"] == 1
    zu_viele = absicht(client, code, art="pool.generieren", anzahl=21)
    assert zu_viele.status_code == 400


def test_der_ausbilder_stellt_die_erzeugung_ein(client, codes):
    code = codes["ausbilderCode"]
    assert (
        absicht(client, code, art="erzeugung.einstellen", erzeugung={"gewichtRd": 0}).status_code
        == 200
    )
    zustand = client.get(f"/api/uebung/{code}/zustand").json()["zustand"]
    assert zustand["erzeugung"]["gewichtRd"] == 0
    assert zustand["erzeugung"]["gewichtBrand"] == 12
    falsch = absicht(client, code, art="erzeugung.einstellen", erzeugung={"gewichtRd": 500})
    assert falsch.status_code == 422
    leer = absicht(client, code, art="erzeugung.einstellen", erzeugung={"kategorie": "GIBTESNICHT"})
    assert leer.status_code == 200
    assert absicht(client, code, art="pool.generieren").status_code == 409


def test_ein_leerer_pool_generiert_nur_wenn_eingestellt(client, codes):
    uebung, _ = client.app.state.uebungen.finden(codes["ausbilderCode"])
    assert uebung.pool_entnehmen().herkunft == "generiert"
    uebung.engine.parameter = uebung.engine.parameter.model_copy(update={"auto_generieren": False})
    assert uebung.pool_entnehmen() is None


def test_ein_fehler_beim_generieren_haelt_die_warteschlange_nicht_an(client, codes):
    import sqlite3

    uebung, _ = client.app.state.uebungen.finden(codes["ausbilderCode"])

    def kaputt(_):
        raise sqlite3.DatabaseError("file is not a database")

    uebung.erzeuger = kaputt
    assert uebung.pool_entnehmen() is None
    client.get(f"/api/uebung/{codes['traineeCode']}/zustand")
    client.get(f"/api/uebung/{codes['ausbilderCode']}/zustand")
    uebung.engine.starten()
    uebung.engine.naechstes_klingeln = uebung.engine.queue_zeit()
    uebung.erzeuger = lambda _: (_ for _ in ()).throw(RuntimeError("unerwartet"))
    with pytest.raises(RuntimeError):
        uebung.engine.takt()
    assert uebung.engine.naechstes_klingeln is not None


def test_null_szenarien_werden_abgelehnt(client, codes):
    assert (
        absicht(client, codes["ausbilderCode"], art="pool.generieren", anzahl=0).status_code == 400
    )


def test_der_ausbilder_korrigiert_gegebene_anleitungen(client, codes):
    a, t = codes["ausbilderCode"], codes["traineeCode"]
    uebung, _ = client.app.state.uebungen.finden(a)
    anruf = uebung.pool_entnehmen()
    from anruf import Anruf

    uebung.anrufe.append(Anruf(szenario=anruf, klingelt_seit=0))
    anruf_id = uebung.anrufe[-1].id
    antwort = absicht(
        client,
        a,
        art="anleitung.korrigieren",
        anrufId=anruf_id,
        anleitung="rd.zugang",
        gegeben=True,
    )
    assert antwort.status_code == 200
    assert uebung.anrufe[-1].korrektur == {"rd.zugang": True}
    zustand = client.get(f"/api/uebung/{a}/zustand").json()["zustand"]
    assert zustand["anrufe"][-1]["korrektur"] == {"rd.zugang": True}
    assert (
        absicht(
            client, t, art="anleitung.korrigieren", anrufId=anruf_id, anleitung="x", gegeben=True
        ).status_code
        == 403
    )
    assert (
        absicht(
            client, a, art="anleitung.korrigieren", anrufId="fehlt", anleitung="x", gegeben=True
        ).status_code
        == 404
    )
    assert absicht(client, a, art="anleitung.korrigieren", anrufId=anruf_id).status_code == 422
    for i in range(99):
        absicht(
            client,
            a,
            art="anleitung.korrigieren",
            anrufId=anruf_id,
            anleitung=f"a{i}",
            gegeben=True,
        )
    voll = absicht(
        client, a, art="anleitung.korrigieren", anrufId=anruf_id, anleitung="neu", gegeben=True
    )
    assert voll.status_code == 422
    wieder = absicht(
        client,
        a,
        art="anleitung.korrigieren",
        anrufId=anruf_id,
        anleitung="rd.zugang",
        gegeben=False,
    )
    assert wieder.status_code == 200


def test_zielzeiten_sind_begrenzt_und_fuer_beide_sichtbar(client, codes):
    a, t = codes["ausbilderCode"], codes["traineeCode"]
    for wert in (5, 1000):
        zu = absicht(client, a, art="engine.parameter", parameter={"zielReanimation": wert})
        assert zu.status_code == 422
    assert (
        absicht(client, a, art="engine.parameter", parameter={"zielUebergabe": 90}).status_code
        == 200
    )
    engine = zustand_von(client, t)["engine"]
    assert engine["ziele"] == {"reanimation": 120, "uebergabe": 90}
    assert "parameter" not in engine
