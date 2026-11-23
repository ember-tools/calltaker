import pytest
from fastapi.testclient import TestClient

from main import anwendung_bauen
from pool import Pool, PoolVoll, UngueltigeDatei
from szenario import Szenario


def szenario(daten, titel="A", **felder):
    return Szenario.model_validate({**daten, "titel": titel, **felder})


def test_hinzufuegen_ersetzen_entfernen_und_verschieben(szenario_daten):
    pool = Pool()
    a = pool.hinzufuegen(szenario(szenario_daten, "A"))
    b = pool.hinzufuegen(szenario(szenario_daten, "B"))
    c = pool.hinzufuegen(szenario(szenario_daten, "C"))
    pool.verschieben(c.id, 0)
    assert [s.titel for s in pool.szenarien] == ["C", "A", "B"]
    pool.verschieben(c.id, 99)
    assert [s.titel for s in pool.szenarien] == ["A", "B", "C"]
    pool.ersetzen(b.model_copy(update={"titel": "B2"}))
    assert pool.finden(b.id).titel == "B2"
    assert pool.entfernen(a.id).titel == "A"
    assert [s.titel for s in pool.szenarien] == ["B2", "C"]
    with pytest.raises(KeyError):
        pool.entfernen(a.id)
    with pytest.raises(KeyError):
        pool.ersetzen(a)
    with pytest.raises(KeyError):
        pool.verschieben(a.id, 0)


def test_eine_doppelte_id_bekommt_eine_neue(szenario_daten):
    pool = Pool()
    erstes = pool.hinzufuegen(szenario(szenario_daten, id="x"))
    zweites = pool.hinzufuegen(szenario(szenario_daten, id="x"))
    assert erstes.id == "x"
    assert zweites.id != "x"


def test_export_und_import_ergeben_denselben_pool(szenario_daten, graph):
    pool = Pool()
    pool.hinzufuegen(szenario(szenario_daten, "A"))
    pool.hinzufuegen(szenario(szenario_daten, "B", herkunft="generiert"))
    datei = pool.exportieren(graph)
    assert datei["format"] == "calltaker-pool"
    assert datei["abfrageVersion"] == graph.meta.version

    neu = Pool()
    befunde = neu.importieren(datei, "ersetzen", graph)
    assert [s.nach_aussen() for s in neu.szenarien] == datei["szenarien"]
    assert all(liste == [] for liste in befunde.values())


def test_anhaengen_behaelt_den_bestand(szenario_daten, graph):
    pool = Pool()
    pool.hinzufuegen(szenario(szenario_daten, "Bestand"))
    datei = pool.exportieren(graph)
    pool.importieren(datei, "anhaengen", graph)
    assert [s.titel for s in pool.szenarien] == ["Bestand", "Bestand"]
    assert len({s.id for s in pool.szenarien}) == 2


def test_veraltete_verweise_werden_aufgenommen_und_gemeldet(szenario_daten, graph):
    pool = Pool()
    pool.hinzufuegen(szenario(szenario_daten, antworten={"rd.weg": {"antwort": "x"}}))
    befunde = Pool().importieren(pool.exportieren(graph), "ersetzen", graph)
    assert [b.meldung for liste in befunde.values() for b in liste] == ["Knoten gibt es nicht mehr"]


@pytest.mark.parametrize(
    "datei",
    [
        {"format": "anders", "version": 1, "abfrageVersion": 1, "szenarien": []},
        {"format": "calltaker-pool", "version": 2, "abfrageVersion": 1, "szenarien": []},
        {
            "format": "calltaker-pool",
            "version": 1,
            "abfrageVersion": 1,
            "szenarien": [{"titel": "x"}],
        },
        [],
    ],
)
def test_ungueltige_dateien_aendern_den_pool_nicht(szenario_daten, graph, datei):
    pool = Pool()
    pool.hinzufuegen(szenario(szenario_daten))
    with pytest.raises(UngueltigeDatei):
        pool.importieren(datei, "ersetzen", graph)
    assert len(pool.szenarien) == 1


def test_die_route_prueft_eine_pooldatei(szenario_daten, graph):
    pool = Pool()
    pool.hinzufuegen(szenario(szenario_daten))
    with TestClient(anwendung_bauen()) as client:
        gut = client.post("/api/pool/pruefen", json=pool.exportieren(graph))
        schlecht = client.post("/api/pool/pruefen", json={"format": "anders"})
    assert gut.status_code == 200
    assert len(gut.json()["szenarien"]) == 1
    assert schlecht.status_code == 422
    assert "format: muss 'calltaker-pool' sein" in schlecht.json()["detail"]
    assert "version: fehlt" in schlecht.json()["detail"]
    assert set(gut.json()["befunde"]) == {s["id"] for s in gut.json()["szenarien"]}


def test_ein_pool_ist_begrenzt(szenario_daten, graph, monkeypatch):
    import pool as pool_modul

    monkeypatch.setattr(pool_modul, "POOL_HOECHSTENS", 2)
    pool = Pool()
    pool.hinzufuegen(szenario(szenario_daten))
    pool.hinzufuegen(szenario(szenario_daten))
    with pytest.raises(PoolVoll):
        pool.hinzufuegen(szenario(szenario_daten))
    datei = pool.exportieren(graph)
    with pytest.raises(PoolVoll):
        pool.importieren(datei, "anhaengen", graph)
    assert len(pool.importieren(datei, "ersetzen", graph)) == 2
