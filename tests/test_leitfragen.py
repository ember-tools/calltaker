import json
import random
import re
import time

import pytest
from fastapi.testclient import TestClient

import leitfragen
import leitfragen_situationen
from einstellungen import einstellungen
from main import anwendung_bauen

KNOTEN = "rd.hauptbeschwerde"
BRUST = "brustschmerzen-andere-beschwerden-in-der"
HERZ = "herzbeschwerden-implantierter"
ATEM = "atembeschwerden"


def geladen(tmp_path, graph, *eintraege):
    (tmp_path / "a.json").write_text(json.dumps({"knoten": list(eintraege)}), "utf-8")
    return leitfragen.laden(tmp_path, graph)


def frage(id_="f", **mehr):
    return {
        "id": id_,
        "frage": "Schmerzen in der Brust?",
        "antworten": [
            {"label": "Ja", "behaelt": [BRUST, HERZ]},
            {"label": "Nein", "nimmt": [BRUST, HERZ]},
            {"label": "Weiß nicht"},
        ],
        **mehr,
    }


def alle_anderen(graph):
    return [a.id for a in graph.knoten[KNOTEN].antworten if a.id not in (BRUST, HERZ)]


def test_der_mitgelieferte_katalog_passt_zum_graphen(graph):
    leitfragen.laden(einstellungen().leitfragen_verzeichnis, graph)


def test_der_katalog_kommt_mit_dem_graphen(graph):
    antwort = TestClient(anwendung_bauen()).get("/api/abfrage")
    assert "leitfragen" in antwort.json()


def test_eine_kachel_ohne_weg_faellt_auf(tmp_path, graph):
    with pytest.raises(ValueError, match=f"Kachel {ATEM} ist über die Leitfragen nicht erreichbar"):
        geladen(tmp_path, graph, {"knoten": KNOTEN, "fragen": [frage()]})


def test_nur_direkt_gewaehlte_kacheln_muessen_nicht_erreichbar_sein(tmp_path, graph):
    eintrag = {"knoten": KNOTEN, "fragen": [frage()], "nurDirekt": alle_anderen(graph)}
    assert geladen(tmp_path, graph, eintrag)[0].knoten == KNOTEN


def test_eine_kachel_ausserhalb_von_nur_direkt_wird_als_unerreichbar_gemeldet(tmp_path, graph):
    eintrag = {"knoten": KNOTEN, "fragen": [frage()], "nurDirekt": alle_anderen(graph)[:-1]}
    with pytest.raises(ValueError, match="Kachel") as fehler:
        geladen(tmp_path, graph, eintrag)
    assert alle_anderen(graph)[-1] in str(fehler.value)
    assert BRUST not in str(fehler.value)


def antworten(*paare):
    return [{"label": label, **mehr} for label, mehr in paare]


@pytest.mark.parametrize(
    ("eintrag", "meldung"),
    [
        ({"knoten": "gibt.es.nicht", "fragen": []}, "gibt.es.nicht: kein Frageknoten"),
        ({"knoten": "rd.alter", "fragen": []}, "rd.alter: kein Frageknoten"),
        ({"knoten": KNOTEN, "fragen": [frage(wenn=["xyz"])]}, "f: Kachel xyz gibt es nicht"),
        (
            {
                "knoten": KNOTEN,
                "fragen": [
                    frage(antworten=antworten(("J", {"behaelt": ["xyz", BRUST]}), ("N", {})))
                ],
            },
            "f: Kachel xyz gibt es nicht",
        ),
        (
            {
                "knoten": KNOTEN,
                "fragen": [frage(antworten=antworten(("J", {"nimmt": ["xyz"]}), ("N", {})))],
            },
            "f: Kachel xyz gibt es nicht",
        ),
        ({"knoten": KNOTEN, "fragen": [], "nurDirekt": ["xyz"]}, "Kachel xyz gibt es nicht"),
        ({"knoten": KNOTEN, "fragen": [frage(), frage()]}, "rd.hauptbeschwerde f: gibt es doppelt"),
        (
            {
                "knoten": KNOTEN,
                "fragen": [frage(antworten=antworten(("Ja", {"behaelt": [BRUST]})))],
            },
            "f: weniger als zwei Antworten",
        ),
        (
            {
                "knoten": KNOTEN,
                "fragen": [frage(antworten=antworten(("Ja", {"behaelt": [BRUST]}), ("Ja", {})))],
            },
            "Antwort „Ja“ gibt es doppelt",
        ),
        (
            {
                "knoten": KNOTEN,
                "fragen": [frage(antworten=antworten(("Ja", {"behaelt": ["xyz"]}), ("N", {})))],
            },
            "„Ja“ lässt keine Kachel übrig",
        ),
        (
            {
                "knoten": KNOTEN,
                "fragen": [
                    frage(),
                    frage("s", sicherheit=True, antworten=antworten(("J", {}), ("N", {}))),
                ],
            },
            "s: Sicherheitsfrage steht hinter einer anderen Frage",
        ),
        (
            {
                "knoten": KNOTEN,
                "fragen": [
                    frage(
                        antworten=antworten(("J", {"behaelt": [BRUST], "nimmt": [HERZ]}), ("N", {}))
                    )
                ],
            },
            "behaelt und nimmt zugleich",
        ),
    ],
)
def test_ein_fehlerhafter_katalog_haelt_den_start_auf(tmp_path, graph, eintrag, meldung):
    with pytest.raises(ValueError, match=meldung):
        geladen(tmp_path, graph, eintrag)


def test_derselbe_knoten_in_zwei_dateien_faellt_auf(tmp_path, graph):
    for name in ("a.json", "b.json"):
        (tmp_path / name).write_text(
            json.dumps({"knoten": [{"knoten": KNOTEN, "fragen": []}]}), "utf-8"
        )
    with pytest.raises(ValueError, match="rd.hauptbeschwerde: gibt es doppelt"):
        leitfragen.laden(tmp_path, graph)


def test_ein_kaputtes_json_nennt_die_datei(tmp_path, graph):
    (tmp_path / "kaputt.json").write_text("{", "utf-8")
    with pytest.raises(ValueError, match="kaputt.json"):
        leitfragen.laden(tmp_path, graph)


def knoten(*fragen):
    return leitfragen.Knotenleitfragen.model_validate({"knoten": "x", "fragen": list(fragen)})


def ja_nein(id_, kachel, **mehr):
    return {
        "id": id_,
        "frage": "?",
        "antworten": [
            {"label": "J", "behaelt": [kachel]},
            {"label": "N", "nimmt": [kachel]},
            {"label": "?"},
        ],
        **mehr,
    }


def test_die_naechste_frage_ist_die_erste_die_noch_unterscheidet():
    sicher = {
        "id": "s",
        "frage": "?",
        "sicherheit": True,
        "wenn": ["3"],
        "antworten": [{"label": "J"}, {"label": "N"}],
    }
    eintrag = knoten(sicher, ja_nein("a", "1"), ja_nein("b", "2"))
    alle = frozenset({"1", "2", "3"})
    assert leitfragen.naechste(eintrag, alle)[1].id == "s"
    assert leitfragen.naechste(eintrag, alle, 1)[1].id == "a"
    assert leitfragen.naechste(eintrag, frozenset({"1", "2"}))[1].id == "a"
    assert leitfragen.naechste(eintrag, frozenset({"2", "3"}), 2)[1].id == "b"
    assert leitfragen.naechste(eintrag, frozenset({"2"}), 1) is None
    assert leitfragen.erreichbare(eintrag, alle) == ({"1", "2", "3"}, True)


def test_eine_frage_die_nichts_unterscheidet_wird_uebersprungen():
    eintrag = knoten(ja_nein("a", "9"), ja_nein("b", "2"))
    assert leitfragen.naechste(eintrag, frozenset({"1", "2"}))[1].id == "b"


def test_eine_antwort_die_nichts_uebrig_liesse_wird_nicht_angeboten():
    frage_ = leitfragen.Leitfrage.model_validate(
        {
            "id": "q",
            "frage": "?",
            "antworten": [
                {"label": "C", "behaelt": ["C"]},
                {"label": "A", "behaelt": ["A"]},
                {"label": "?"},
            ],
        }
    )
    assert [a.label for a in frage_.angeboten(frozenset({"A", "B"}))] == ["A", "?"]
    assert frage_.offen(frozenset({"A", "B"}))


def test_eine_sicherheitsfrage_die_nichts_einschraenkt_haelt_den_weg_nicht_auf():
    sicher = {
        "id": "s",
        "frage": "?",
        "sicherheit": True,
        "antworten": [{"label": "J"}, {"label": "N"}],
    }
    eintrag = knoten(sicher, ja_nein("a", "1"))
    assert leitfragen.erreichbare(eintrag, frozenset({"1", "2"})) == ({"1", "2"}, True)


def test_ein_katalog_in_echter_groesse_wird_schnell_geprueft():
    zufall = random.Random(24)
    kacheln = [f"k{i}" for i in range(35)]
    fragen = [
        {
            "id": f"q{i}",
            "frage": "?",
            "antworten": [
                {"label": "J", "behaelt": zufall.sample(kacheln, zufall.randint(3, 12))},
                {"label": "N", "nimmt": zufall.sample(kacheln, zufall.randint(1, 6))},
                {"label": "?"},
            ],
        }
        for i in range(24)
    ]
    beginn = time.perf_counter()
    assert leitfragen.erreichbare(knoten(*fragen), frozenset(kacheln)) == (set(kacheln), True)
    assert time.perf_counter() - beginn < 1


def test_ein_unerreichbarer_katalog_in_echter_groesse_scheitert_schnell():
    zufall = random.Random(30)
    kacheln = [f"k{i}" for i in range(35)]
    ohne = kacheln[1:]
    fragen = [
        {
            "id": f"q{i}",
            "frage": "?",
            "antworten": [
                {"label": "J", "behaelt": zufall.sample(ohne, zufall.randint(3, 12))},
                {"label": "N", "nimmt": zufall.sample(ohne, zufall.randint(1, 6))},
                {"label": "?"},
            ],
        }
        for i in range(30)
    ]
    beginn = time.perf_counter()
    fehler = leitfragen.knotenfehler(knoten(*fragen), frozenset(kacheln))
    assert time.perf_counter() - beginn < 10
    assert any("k0" in f for f in fehler)


def fragen_bis(eintrag, alle, kachel):
    kacheln, ab, anzahl = alle, 0, 0
    while (naechste := leitfragen.naechste(eintrag, kacheln, ab)) is not None:
        stelle, frage = naechste
        reste = [antwort.rest(kacheln) for antwort in frage.angeboten(kacheln)]
        kacheln = min((rest for rest in reste if kachel in rest), key=len)
        ab, anzahl = stelle + 1, anzahl + 1
    return anzahl, kacheln


def test_jede_hauptbeschwerde_ist_in_wenigen_fragen_vorgeschlagen(graph):
    katalog = leitfragen.laden(einstellungen().leitfragen_verzeichnis, graph)
    eintrag = next(e for e in katalog if e.knoten == KNOTEN)
    alle = frozenset(a.id for a in graph.knoten[KNOTEN].antworten)
    for kachel in alle:
        anzahl, rest = fragen_bis(eintrag, alle, kachel)
        assert anzahl <= 12, kachel
        assert kachel in rest and len(rest) <= leitfragen.HOECHSTENS_VORGESCHLAGEN


def test_jede_situation_der_notfallrettung_hat_leitfragen_in_ertraeglicher_laenge(graph):
    katalog = {e.knoten: e for e in leitfragen.laden(einstellungen().leitfragen_verzeichnis, graph)}
    situationen = leitfragen_situationen.situationsknoten(graph)
    assert situationen and set(situationen) <= set(katalog)
    mittel = []
    for knoten in situationen:
        eintrag = katalog[knoten]
        alle = frozenset(a.id for a in graph.knoten[knoten].antworten)
        gefragt = [fragen_bis(eintrag, alle, k)[0] for k in alle - set(eintrag.nur_direkt)]
        mittel.append(sum(gefragt) / len(gefragt))
        assert mittel[-1] <= 18, knoten
    assert sum(mittel) / len(mittel) <= 8


def test_die_situationsfragen_sind_frisch_erzeugt(graph):
    werkzeug = leitfragen_situationen
    gespeichert = json.loads(werkzeug.ZIEL.read_text("utf-8"))
    assert werkzeug.katalog(graph) == gespeichert


def test_ein_ja_nimmt_nie_eine_schwerere_situation_heraus(graph):
    werkzeug = leitfragen_situationen
    inhaltlich = {werkzeug.kennung(z.frage) for z in werkzeug.ZUSATZ} | {
        v.id for vorab in werkzeug.VORAB.values() for v in vorab
    }
    for eintrag in werkzeug.katalog(graph)["knoten"]:
        stufe = werkzeug.stufen(graph, eintrag["knoten"])
        direkt = set(eintrag.get("nurDirekt", []))
        for frage in eintrag["fragen"]:
            ja, nein = frage["antworten"][0], frage["antworten"][1]
            if ja["label"] != "Ja" or "behaelt" in ja or not nein.get("nimmt"):
                continue
            gruppe = set(nein["nimmt"])
            if frage["id"] in inhaltlich:
                continue
            unterste = min(stufe[k] for k in gruppe)
            herausgenommen = set(ja.get("nimmt", [])) - direkt
            assert all(stufe[k] <= unterste for k in herausgenommen), (
                eintrag["knoten"],
                frage["id"],
            )


def test_die_situationsfragen_schreiben_nomen_gross():
    graph = leitfragen_situationen.laden(leitfragen_situationen.WURZEL / "daten" / "abfrage")
    texte = [
        f["frage"] for e in leitfragen_situationen.katalog(graph)["knoten"] for f in e["fragen"]
    ]
    kleine_nomen = {nomen.lower() for nomen in leitfragen_situationen.NOMEN}
    for text in texte:
        assert not kleine_nomen & set(re.findall(r"[a-zäöüß]+", text)), text


def test_strom_beim_wasserschaden_ist_eine_eigene_frage(graph):
    for umfang in ("einzelne-wohnung", "mehrere-geschosse"):
        ziel = graph.antwort("fw.th.wasserschaden.k1", umfang).ziel
        strom = graph.knoten[ziel]
        assert "Strom" in strom.frage and strom.hinweis
        assert graph.antwort(ziel, "ja-strom-im-spiel").ziel == "fw.th.wasserschaden.k5"
    assert graph.antwort("fw.th.wasserschaden.k1", "elektroanlage-betroffen") is None
    keller = graph.antwort("fw.th.wasserschaden.k2", "keller").ziel
    assert graph.antwort(keller, "ja-strom-im-spiel") is not None


def test_brand_und_technische_hilfe_stellen_sicherheitsfragen_zuerst(graph):
    katalog = {e.knoten: e for e in leitfragen.laden(einstellungen().leitfragen_verzeichnis, graph)}
    for knoten in ("fw.grund", "fw.th.grund"):
        assert knoten in katalog
    sicher = [e for e in katalog.values() if any(f.sicherheit for f in e.fragen)]
    protokolle = {e.knoten.rsplit(".", 1)[0] for e in sicher}
    assert {"fw.th.wasserschaden", "fw.brand.gebaeudebrand", "fw.th.gefahrstoffe"} <= protokolle
    for eintrag in sicher:
        assert all(f.hinweis for f in eintrag.fragen if f.sicherheit), eintrag.knoten
        assert eintrag.knoten.startswith("fw.")
    strom = next(f for f in katalog["fw.th.wasserschaden.k0"].fragen if f.id == "strom")
    assert strom.sicherheit and "Wasser" in strom.hinweis


def test_der_wasserschaden_verliert_und_gewinnt_keinen_code(graph):
    codes = {e.code for e in graph.endpunkte if e.protokoll == "fw.th.wasserschaden"}
    knoten = {
        k.code for i, k in graph.knoten.items() if i.startswith("fw.th.wasserschaden") and k.code
    }
    assert codes == knoten and len(codes) == 20
    for frage, antwort, nein in (
        ("fw.th.wasserschaden.k1", "einzelne-wohnung", "fw.th.wasserschaden.k3"),
        ("fw.th.wasserschaden.k1", "mehrere-geschosse", "fw.th.wasserschaden.k4"),
        ("fw.th.wasserschaden.k2", "keller", "fw.th.wasserschaden.k6"),
    ):
        strom = graph.antwort(frage, antwort).ziel
        assert graph.antwort(strom, "nein-kein-strom").ziel == nein


def erster_frageknoten(graph, ziel):
    while not graph.knoten[ziel].antworten:
        knoten = graph.knoten[ziel]
        ziel = knoten.ziel or next(iter(knoten.weiche.ziele.values()))
    return ziel


def test_sicherheitsfragen_stehen_am_ersten_frageknoten_ihres_protokolls(graph):
    katalog = leitfragen.laden(einstellungen().leitfragen_verzeichnis, graph)
    erste = {
        erster_frageknoten(graph, antwort.ziel)
        for wahl in ("fw.grund", "fw.th.grund")
        for antwort in graph.knoten[wahl].antworten
    }
    for eintrag in katalog:
        if any(f.sicherheit for f in eintrag.fragen):
            assert eintrag.knoten in erste, eintrag.knoten


def gefuehrt(eintrag, alle, antworten):
    kacheln, ab = alle, 0
    while (naechste := leitfragen.naechste(eintrag, kacheln, ab)) is not None:
        stelle, frage = naechste
        gewaehlt = antworten.get(frage.id, "Weiß nicht")
        antwort = next(a for a in frage.angeboten(kacheln) if a.label == gewaehlt)
        kacheln, ab = antwort.rest(kacheln), stelle + 1
    return kacheln


@pytest.mark.parametrize(
    ("knoten", "antworten", "korrekt"),
    [
        (
            "fw.grund",
            {
                "bma": "Nein",
                "explosion": "Nein",
                "melder": "Nein",
                "flammen": "Ja, Flammen",
                "was-brennt": "Ein Gebäude oder eine Wohnung",
                "sonderobjekt": "Nein",
                "betrieb": "Nein",
            },
            "gebaeudebrand",
        ),
        (
            "fw.grund",
            {
                "bma": "Nein",
                "explosion": "Nein",
                "melder": "Nein",
                "flammen": "Ja, Flammen",
                "was-brennt": "Ein Fahrzeug",
            },
            "brand-in-verkehrsanlagen",
        ),
        (
            "fw.grund",
            {
                "bma": "Nein",
                "explosion": "Nein",
                "melder": "Nein",
                "flammen": "Ja, Flammen",
                "was-brennt": "Ein Fahrzeug",
            },
            "fahrzeugbrand",
        ),
        (
            "fw.grund",
            {
                "bma": "Nein",
                "explosion": "Nein",
                "melder": "Nein",
                "flammen": "Nein, nur Rauch oder Geruch",
                "was-brennt": "Ein Gebäude oder eine Wohnung",
                "sonderobjekt": "Nein",
                "betrieb": "Nein",
            },
            "rauchentwicklung-brandgeruch",
        ),
        (
            "fw.grund",
            {"bma": "Nein", "explosion": "Nein", "melder": "Ja"},
            "rauchentwicklung-brandgeruch",
        ),
        ("fw.grund", {"bma": "Ja"}, "brandmeldeanlage"),
        (
            "fw.grund",
            {
                "bma": "Nein",
                "explosion": "Nein",
                "melder": "Nein",
                "flammen": "Nein, nur Rauch oder Geruch",
                "was-brennt": "Nichts zu sehen, es riecht nur nach Brand",
            },
            "rauchentwicklung-brandgeruch",
        ),
        ("fw.grund", {"bma": "Nein", "explosion": "Nein", "melder": "Ja"}, "gebaeudebrand"),
        (
            "fw.th.grund",
            {"was-passiert": "Sturm: Baum, Dach oder Bauteil", "verschuettet": "Ja"},
            "sturmschaden",
        ),
        (
            "fw.th.grund",
            {"was-passiert": "Etwas ist eingestürzt oder droht einzustürzen", "verschuettet": "Ja"},
            "einsturz-gebaeudeschaden",
        ),
        (
            "fw.th.grund",
            {"was-passiert": "Etwas ist eingestürzt oder droht einzustürzen", "verschuettet": "Ja"},
            "person-in-notlage",
        ),
        (
            "fw.th.grund",
            {"was-passiert": "Wasser im Gebäude oder Überflutung", "tuer": "Ja"},
            "tueroeffnung",
        ),
        (
            "fw.th.grund",
            {
                "was-passiert": "Eine Tür muss geöffnet werden, oder jemand steckt im Aufzug fest",
                "aufzug": "Ja",
            },
            "aufzugnotbefreiung",
        ),
    ],
)
def test_ehrliche_anrufe_bei_brand_und_technischer_hilfe_fuehren_zur_korrekten_kachel(
    graph, knoten, antworten, korrekt
):
    katalog = {e.knoten: e for e in leitfragen.laden(einstellungen().leitfragen_verzeichnis, graph)}
    alle = frozenset(a.id for a in graph.knoten[knoten].antworten)
    rest = gefuehrt(katalog[knoten], alle, antworten)
    assert korrekt in rest and len(rest) <= leitfragen.HOECHSTENS_VORGESCHLAGEN, rest
