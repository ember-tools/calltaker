import json
import random
import time

import pytest
from fastapi.testclient import TestClient

import leitfragen
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
