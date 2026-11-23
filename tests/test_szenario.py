import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from abfrage import laden
from main import anwendung_bauen
from szenario import Szenario, pruefen


def test_ein_szenario_wird_gelesen_und_nummern_normalisiert(szenario_daten, graph):
    szenario = Szenario.model_validate(szenario_daten)
    assert szenario.anrufer.rufnummer == "493068532207"
    assert szenario.anrufer.erreichbar_unter() == "493068532207"
    assert szenario.herkunft == "vorbereitet"
    assert pruefen(szenario, graph) == []


def test_auf_dem_draht_sind_die_felder_in_camel_case(szenario_daten):
    aussen = Szenario.model_validate(szenario_daten).nach_aussen()
    assert aussen["abfrageVersion"] == szenario_daten["abfrageVersion"]
    assert aussen["anrufer"]["rufnummerUnterdrueckt"] is False
    assert Szenario.model_validate(aussen).nach_aussen() == aussen


@pytest.mark.parametrize(
    ("anrufer", "meldung"),
    [
        ({"name": "X"}, "ohne Unterdrückung ist eine Rufnummer Pflicht"),
        ({"name": "X", "rufnummerUnterdrueckt": True}, "Rückrufnummer Pflicht"),
    ],
)
def test_ohne_erreichbare_nummer_kein_szenario(szenario_daten, anrufer, meldung):
    with pytest.raises(ValidationError, match=meldung):
        Szenario.model_validate({**szenario_daten, "anrufer": anrufer})


def test_unterdrueckt_mit_rueckrufnummer(szenario_daten):
    anrufer = {"name": "X", "rufnummerUnterdrueckt": True, "rueckrufnummer": "0176 1234567"}
    szenario = Szenario.model_validate({**szenario_daten, "anrufer": anrufer})
    assert szenario.anrufer.erreichbar_unter() == "491761234567"


def test_unbekannte_felder_werden_abgelehnt(szenario_daten):
    with pytest.raises(ValidationError):
        Szenario.model_validate({**szenario_daten, "titl": "x"})


def befunde_von(szenario_daten, graph, **aenderungen):
    return [
        (b.art, b.meldung)
        for b in pruefen(Szenario.model_validate({**szenario_daten, **aenderungen}), graph)
    ]


def test_fehlende_knoten_und_antworten_werden_gemeldet(szenario_daten, graph):
    antworten = {
        **szenario_daten["antworten"],
        "rd.gibtesnicht": {"antwort": "x"},
        "rd.atmung": {"antwort": "gibtesnicht"},
        "rd.alter": {"antwort": "81"},
        "eroeffnung.weiche": {"antwort": "rd"},
    }
    befunde = befunde_von(szenario_daten, graph, antworten=antworten)
    assert ("fehler", "Knoten gibt es nicht mehr") in befunde
    assert ("fehler", "Antwort gibtesnicht gibt es nicht mehr") in befunde
    assert ("fehler", "hier wird getippt, nicht gewählt") in befunde
    assert ("fehler", "an diesem Knoten wird nicht gefragt") in befunde


def test_geaenderte_labels_und_versionen_sind_warnungen(szenario_daten, graph):
    knoten, wahl = next(iter(szenario_daten["antworten"].items()))
    antworten = {**szenario_daten["antworten"], knoten: {**wahl, "label": "alter Text"}}
    befunde = befunde_von(szenario_daten, graph, antworten=antworten, abfrageVersion=0)
    arten = {art for art, _ in befunde}
    assert arten == {"warnung"}
    assert len(befunde) == 2


def test_das_ziel_muss_ein_endpunkt_sein(szenario_daten, graph):
    assert befunde_von(szenario_daten, graph, ziel={"knoten": "rd.atmung", "code": "X"}) == [
        ("fehler", "Endpunkt gibt es nicht mehr")
    ]
    ziel = {**szenario_daten["ziel"], "code": "99Z99"}
    assert befunde_von(szenario_daten, graph, ziel=ziel)[0][0] == "warnung"


def test_die_route_prueft_ein_szenario(szenario_daten):
    with TestClient(anwendung_bauen()) as client:
        antwort = client.post("/api/szenario/pruefen", json={**szenario_daten, "abfrageVersion": 0})
        kaputt = client.post(
            "/api/szenario/pruefen", json={**szenario_daten, "anrufer": {"name": "X"}}
        )
    assert antwort.status_code == 200
    assert antwort.json()["befunde"][0]["art"] == "warnung"
    assert antwort.json()["szenario"]["anrufer"]["rufnummer"] == "493068532207"
    assert kaputt.status_code == 422


def test_auswahlen_brauchen_eine_antwort(szenario_daten, graph):
    antworten = {**szenario_daten["antworten"], "rd.atmung": {"wert": "ja"}}
    befunde = befunde_von(szenario_daten, graph, antworten=antworten)
    assert ("fehler", "hier wird gewählt, nicht getippt") in befunde


def test_eingaben_ohne_leerfall_brauchen_einen_wert(szenario_daten, tmp_path):
    (tmp_path / "meta.json").write_text(
        json.dumps({"version": 1, "wurzel": "frage", "quelle": "Test"})
    )
    knoten = {
        "frage": {
            "frage": "Wer?",
            "eingabe": {"vorlage": "{wert}", "platzhalter": "Name"},
            "ziel": "ende",
        },
        "ende": {"code": "X"},
    }
    (tmp_path / "a.json").write_text(json.dumps({"knoten": knoten}))
    klein = laden(tmp_path)
    szenario = Szenario.model_validate(
        {**szenario_daten, "antworten": {"frage": {}}, "abfrageVersion": 1}
    )
    befunde = [(b.art, b.meldung) for b in pruefen(szenario, klein)]
    assert ("fehler", "hier fehlt der getippte Wert") in befunde


def test_eine_eingabe_mit_leerfall_darf_leer_bleiben(szenario_daten, graph):
    leerbar = next(i for i, k in graph.knoten.items() if k.eingabe is not None and k.eingabe.leer)
    antworten = {**szenario_daten["antworten"], leerbar: {}}
    assert befunde_von(szenario_daten, graph, antworten=antworten) == []


def test_eine_unterdrueckte_nummer_wird_nicht_angezeigt(szenario_daten):
    anrufer = {
        "name": "X",
        "rufnummer": "030 1",
        "rufnummerUnterdrueckt": True,
        "rueckrufnummer": "0176 1234567",
    }
    with pytest.raises(ValidationError, match="unterdrückte Rufnummer wird nicht angezeigt"):
        Szenario.model_validate({**szenario_daten, "anrufer": anrufer})


def test_die_route_meldet_fehler_auf_deutsch(szenario_daten):
    with TestClient(anwendung_bauen()) as client:
        ohne_nummer = client.post(
            "/api/szenario/pruefen", json={**szenario_daten, "anrufer": {"name": "X"}}
        )
        ohne_titel = client.post(
            "/api/szenario/pruefen", json={k: v for k, v in szenario_daten.items() if k != "titel"}
        )
    assert ohne_nummer.json()["detail"] == "anrufer: ohne Unterdrückung ist eine Rufnummer Pflicht"
    assert ohne_titel.json()["detail"] == "titel: fehlt"
