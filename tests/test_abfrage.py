import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api
from abfrage import laden
from abfrage_uebernehmen import GEDANKENSTRICH, ZielNichtLeer, altersgrenze, slug, text
from abfrage_uebernehmen import schreiben as uebernahme_schreiben
from einstellungen import einstellungen
from main import anwendung_bauen

META = {"version": 1, "wurzel": "start", "quelle": "Test"}
ENDE = {"code": "01A01", "kategorie": "RD5."}


def schreiben(verzeichnis: Path, meta: dict = META, **dateien: dict) -> Path:
    (verzeichnis / "meta.json").write_text(json.dumps(meta))
    for name, knoten in dateien.items():
        (verzeichnis / f"{name}.json").write_text(json.dumps({"knoten": knoten}))
    return verzeichnis


def auswahl(*ziele: str, **felder) -> dict:
    antworten = [{"id": f"a{i}", "label": z, "ziel": z} for i, z in enumerate(ziele)]
    return {"frage": "Frage?", "antworten": antworten, **felder}


def test_der_graph_beginnt_mit_der_fachrichtung(graph):
    wurzel = graph.knoten[graph.meta.wurzel]
    assert wurzel.frage == "Was ist jetzt der Grund Ihres Anrufes?"
    assert [a.id for a in wurzel.antworten] == ["rd", "brand", "th"]
    assert {a.ziel for a in wurzel.antworten} == {"eroeffnung.hand"}


def test_die_eroeffnung_ist_gemeinsam_und_verzweigt_ueber_die_weiche(graph):
    assert graph.knoten["eroeffnung.hand"].antworten[0].ziel == "eroeffnung.vor-ort"
    assert {a.ziel for a in graph.knoten["eroeffnung.vor-ort"].antworten} == {"eroeffnung.weiche"}
    weiche = graph.knoten["eroeffnung.weiche"].weiche
    assert weiche.knoten == "fachrichtung"
    assert weiche.ziele == {"rd": "rd.anzahl", "brand": "fw.grund", "th": "fw.th.grund"}
    assert graph.knoten["rd.alter"].eingabe is not None


def test_geschoss_und_gefahren_gehoeren_nicht_zur_abfrage(graph):
    fragen = {knoten.frage for knoten in graph.knoten.values()}
    assert "Geschoss und Name am Klingelschild?" not in fragen
    assert "Gefahren an der Einsatzstelle?" not in fragen


def test_jeder_pfad_des_index_fuehrt_zu_seinem_endpunkt(graph):
    for endpunkt in graph.endpunkte:
        aktuell = endpunkt.pfad[0].knoten
        for schritt in endpunkt.pfad:
            assert schritt.knoten == aktuell
            knoten = graph.knoten[aktuell]
            if knoten.antworten is not None:
                aktuell = graph.antwort(aktuell, schritt.antwort).ziel
            elif knoten.weiche is not None:
                aktuell = knoten.weiche.ziele[schritt.antwort]
            else:
                aktuell = knoten.ziel
        assert aktuell == endpunkt.knoten
        assert graph.knoten[aktuell].code == endpunkt.code


def test_der_index_fuehrt_jeden_endpunkt_einmal_je_protokoll(graph):
    paare = [(e.protokoll, e.knoten) for e in graph.endpunkte]
    assert len(paare) == len(set(paare))
    endpunkte = {id_ for id_, knoten in graph.knoten.items() if knoten.code is not None}
    assert {e.knoten for e in graph.endpunkte} == endpunkte
    assert {e.fachrichtung for e in graph.endpunkte} == {"rd", "brand", "th"}
    assert {e.protokoll.split(".")[1] for e in graph.endpunkte if e.fachrichtung != "rd"} == {
        "brand",
        "th",
    }
    assert all(
        e.protokoll.startswith(f"fw.{e.fachrichtung}.")
        for e in graph.endpunkte
        if e.fachrichtung != "rd"
    )


def test_gleiche_codes_mit_verschiedener_kategorie_bleiben_im_index(graph):
    varianten = {
        (e.kategorie, e.anlass)
        for e in graph.endpunkte
        if (e.protokoll, e.code) == ("rd.01", "01A02")
    }
    assert len(varianten) == 2


def test_labels_tragen_keine_html_zeichen(graph):
    for knoten in graph.knoten.values():
        for antwort in knoten.antworten or []:
            assert "&nbsp;" not in antwort.label
            assert "  " not in antwort.label


def test_ein_gueltiger_kleiner_graph(tmp_path):
    graph = laden(schreiben(tmp_path, a={"start": auswahl("ende"), "ende": ENDE}))
    assert list(graph.knoten) == ["start", "ende"]


@pytest.mark.parametrize(
    ("knoten", "meldung"),
    [
        ({"start": auswahl("fehlt")}, "Ziel fehlt gibt es nicht"),
        ({"start": auswahl("b"), "b": auswahl("start")}, "liegt auf einem Zyklus"),
        ({"start": auswahl("ende"), "ende": ENDE, "los": ENDE}, "los ist von der Wurzel"),
        (
            {
                "start": auswahl("w"),
                "w": {"weiche": {"knoten": "start", "ziele": {"falsch": "ende"}}},
                "ende": ENDE,
            },
            "Weiche deckt nicht genau",
        ),
        (
            {"start": auswahl("w"), "w": {"weiche": {"knoten": "ende", "ziele": {}}}, "ende": ENDE},
            "das keine Auswahl ist",
        ),
        (
            {
                "start": auswahl("w", "b"),
                "b": auswahl("w"),
                "w": {"weiche": {"knoten": "b", "ziele": {"a0": "ende"}}},
                "ende": ENDE,
            },
            "ohne dass b gefragt wurde",
        ),
        (
            {
                "start": {
                    "frage": "?",
                    "antworten": [
                        {"id": "x", "label": "1", "ziel": "ende"},
                        {"id": "x", "label": "2", "ziel": "ende"},
                    ],
                },
                "ende": ENDE,
            },
            "Antwort-ID x doppelt",
        ),
        (
            {
                "start": {
                    "frage": "?",
                    "antworten": [
                        {"id": "a", "label": "1", "ziel": "ende", "protokoll": "start.p"},
                        {"id": "b", "label": "2", "ziel": "ende", "protokoll": "start.p"},
                    ],
                },
                "ende": ENDE,
            },
            "führt hier aber nicht in seine eigenen Knoten",
        ),
        (
            {
                "start": {
                    "frage": "?",
                    "antworten": [{"id": "a", "label": "1", "ziel": "ende", "protokoll": "xx.p"}],
                },
                "ende": ENDE,
            },
            "gehört zu keiner Fachrichtung",
        ),
        ({"Start": auswahl("ende"), "ende": ENDE}, "passt nicht zum Muster"),
    ],
)
def test_strukturfehler_werden_gemeldet(tmp_path, knoten, meldung):
    with pytest.raises(ValueError, match=meldung):
        laden(schreiben(tmp_path, a=knoten))


@pytest.mark.parametrize(
    ("knoten", "meldung"),
    [
        ({"frage": "?", "code": "1", "antworten": []}, "genau Auswahl, Eingabe"),
        ({**auswahl("ende"), "ziel": "ende"}, "aber kein Ziel"),
        ({"frage": "?", "eingabe": {"vorlage": "{wert}", "platzhalter": "x"}}, "Frage und Ziel"),
        ({"weiche": {"knoten": "x", "ziele": {}}, "ziel": "ende"}, "kein eigenes Ziel"),
        ({"code": "1", "ziel": "ende"}, "führt nirgends hin"),
        ({**auswahl("ende"), "frgae": "x"}, "Extra inputs"),
    ],
)
def test_falsche_knoten_werden_mit_datei_und_id_gemeldet(tmp_path, knoten, meldung):
    with pytest.raises(ValueError, match=rf"^a\.json: start: .*{meldung}"):
        laden(schreiben(tmp_path, a={"start": knoten, "ende": ENDE}))


def test_eine_fehlende_wurzel_wird_gemeldet(tmp_path):
    with pytest.raises(ValueError, match="Wurzel start gibt es nicht"):
        laden(schreiben(tmp_path, a={"ende": ENDE}))


def test_ein_knoten_in_zwei_dateien_wird_gemeldet(tmp_path):
    with pytest.raises(ValueError, match="b.json: Knoten ende gibt es doppelt"):
        laden(schreiben(tmp_path, a={"start": auswahl("ende"), "ende": ENDE}, b={"ende": ENDE}))


@pytest.mark.parametrize(
    ("inhalt", "meldung"),
    [("{kaputt", "a.json: .*Invalid JSON"), ('{"knotn": {}}', "a.json: .*knoten")],
)
def test_kaputte_dateien_werden_mit_namen_gemeldet(tmp_path, inhalt, meldung):
    schreiben(tmp_path)
    (tmp_path / "a.json").write_text(inhalt)
    with pytest.raises(ValueError, match=meldung):
        laden(tmp_path)


def test_ein_kaputter_graph_verhindert_den_start(tmp_path, monkeypatch):
    schreiben(tmp_path, a={"start": auswahl("fehlt")})
    monkeypatch.setattr(einstellungen(), "abfrage_verzeichnis", tmp_path)
    api.abfragegraph.cache_clear()
    api.abfragebuendel.cache_clear()
    try:
        with pytest.raises(ValueError, match="Ziel fehlt"), TestClient(anwendung_bauen()):
            pass
    finally:
        api.abfragegraph.cache_clear()
        api.abfragebuendel.cache_clear()


@pytest.mark.parametrize(
    ("label", "grenze"),
    [
        ("Ohnmacht oder Beinahe-Ohnmacht ≥ 50", {"min": 50}),
        ("Aschfahle oder graue Hautfarbe gemeldet ≥50", {"min": 50}),
        ("Brustschmerzen/Beschwerden in der Brust < 35 (ohne Notfallleitsymptome)", {"max": 34}),
        ("bei Patientenalter bis 12 Jahre", {"max": 12}),
        ("bei Patientenalter älter 12 Jahre, Trauma", {"min": 13}),
        ("bei Patientenalter älter 17 Jahre", {"min": 18}),
        ("bei Patientenalter 13 bis 17 Jahre", {"min": 13, "max": 17}),
        ("Patientenalter zwischen 13 und 55 Jahren", {"min": 13, "max": 55}),
        ("bei Patientenalter älter 56 Jahre", {"min": 57}),
        ("bei Patientenalter bis 30 Tage", {"max": 0}),
        ("Krampfanfall (≤ 6, keine Epilepsie bestätigt)", {"max": 6}),
        ("Krampfanfall (> 6, keine Epilepsie bestätigt)", {"min": 7}),
        ("bei Patientenalter älter 30 Tage", None),
        ("Puls < 50 oder Puls ≥ 130 (ohne Notfallleitsymptome)", None),
        ("Einzelne ÄLTERE (≥ 6 h) ZENTRALE Wunde", None),
        ("STURZ AUS EXTREMER HÖHE (≥ 10 m)", None),
        ("Keine Verletzungen gemeldet (unbestätigt oder ≥ 5 Personen beteiligt)", None),
    ],
)
def test_altersgrenzen_aus_dem_label(label, grenze):
    assert altersgrenze(label) == grenze


def test_ids_und_texte_der_uebernahme():
    assert slug("Brand im Freien / Ödland") == "brand-im-freien-oedland"
    assert (
        slug("4. Hand - der Anrufer hat es nur gehört oder gesehen")
        == "4-hand-der-anrufer-hat-es-nur-gehoert"
    )
    assert text(f"1. Hand {GEDANKENSTRICH} der Anrufer") == "1. Hand: der Anrufer"
    assert text("Bewusstlosigkeit – AGONALE&nbsp; Atmung") == "Bewusstlosigkeit: AGONALE Atmung"
    assert text("Alter 12–50") == "Alter 12–50"


def test_die_route_liefert_den_graphen_gepackt():
    with TestClient(anwendung_bauen()) as client:
        antwort = client.get("/api/abfrage", headers={"Accept-Encoding": "gzip"})
    assert antwort.status_code == 200
    assert antwort.headers["content-encoding"] == "gzip"
    buendel = antwort.json()
    assert buendel["meta"]["wurzel"] == "fachrichtung"
    assert len(buendel["endpunkte"]) > 3000
    assert buendel["knoten"]["fachrichtung"]["antworten"][0]["label"] == "Notfallrettung"


def test_die_uebernahme_schreibt_nicht_in_fremde_ordner(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    with pytest.raises(ZielNichtLeer):
        uebernahme_schreiben(tmp_path, {"meta.json": META})
    assert (tmp_path / "package.json").is_file()


def test_die_uebernahme_ersetzt_einen_vorhandenen_graphen(tmp_path):
    uebernahme_schreiben(tmp_path, {"meta.json": META, "alt.json": {"start": ENDE}})
    uebernahme_schreiben(tmp_path, {"meta.json": META, "neu.json": {"start": ENDE}})
    assert sorted(p.name for p in tmp_path.iterdir()) == ["meta.json", "neu.json"]


def test_ein_protokoll_darf_an_zwei_stellen_in_seine_knoten_fuehren(tmp_path):
    knoten = {
        "start": {
            "frage": "?",
            "antworten": [
                {"id": "a", "label": "1", "ziel": "a.p.k0", "protokoll": "a.p"},
                {"id": "b", "label": "2", "ziel": "a.p.k1", "protokoll": "a.p"},
            ],
        },
        "a.p.k0": auswahl("a.p.k1"),
        "a.p.k1": auswahl("a.p.ende"),
        "a.p.ende": ENDE,
    }
    graph = laden(schreiben(tmp_path, a=knoten))
    [endpunkt] = graph.endpunkte
    assert [s.antwort for s in endpunkt.pfad][0] == "b"


def test_wer_nicht_atmet_kommt_gleich_zum_kreislaufstillstand(graph):
    atmung = graph.antwort("rd.atmung", "atmet-nicht")
    assert (atmung.protokoll, atmung.ziel) == ("rd.09", "rd.09.todeszeichen")
    todeszeichen = graph.knoten["rd.09.todeszeichen"]
    assert todeszeichen.antworten[0].ziel == "rd.09.k6"
    stillstand = [e for e in graph.endpunkte if e.code == "09E01"]
    assert {e.pfad[0].knoten for e in stillstand} == {"rd.atmung"}
    assert {e.kategorie for e in stillstand} == {"RD1NC REA.", "RD1NC NNAD."}
    tot = [e for e in graph.endpunkte if e.code.startswith("09B01")]
    assert {e.pfad[0].knoten for e in tot} == {"rd.atmung"}
    assert graph.tiefen["rd.atmung"] < graph.tiefen["rd.hauptbeschwerde"]
