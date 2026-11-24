import random

import pytest

from stimmigkeit import (
    AUTOMATISCH,
    BEIM_BETROFFENEN,
    FUER_ANDERE,
    GEHOERT,
    SELBST,
    VOR_ORT_JA,
    WACH,
    stimmigkeitsmeldungen,
)
from szenario import Szenario, pruefen
from szenariogenerator import Erzeugung, Quellen, generieren

NICHT_DA = "nein-war-nicht-vor-ort"


def mit(szenario_daten, hand=BEIM_BETROFFENEN, vor_ort=VOR_ORT_JA, **antworten):
    daten = {
        **szenario_daten,
        "antworten": {
            **szenario_daten["antworten"],
            "eroeffnung.hand": {"antwort": hand},
            "eroeffnung.vor-ort": {"antwort": vor_ort},
            **{knoten.replace("_", "."): {"antwort": a} for knoten, a in antworten.items()},
        },
    }
    return Szenario.model_validate(daten)


def meldungen(graph, szenario):
    return stimmigkeitsmeldungen(graph, szenario)


def test_ein_stimmiges_szenario_hat_keine_warnung(graph, szenario_daten):
    assert meldungen(graph, mit(szenario_daten)) == []
    assert meldungen(graph, mit(szenario_daten, FUER_ANDERE, NICHT_DA)) == []


@pytest.mark.parametrize("hand", [FUER_ANDERE, GEHOERT, AUTOMATISCH])
def test_wer_nicht_beim_betroffenen_ist_ist_nicht_vor_ort(graph, szenario_daten, hand):
    assert "3./4. Hand oder automatische Meldung, aber Anrufer vor Ort" in meldungen(
        graph, mit(szenario_daten, hand)
    )


def test_erste_und_zweite_hand_sind_vor_ort(graph, szenario_daten):
    gemeldet = meldungen(graph, mit(szenario_daten, BEIM_BETROFFENEN, NICHT_DA))
    assert "1./2. Hand, aber Anrufer nicht vor Ort" in gemeldet


def test_wer_selbst_anruft_ist_wach_und_kennt_seine_atmung(graph, szenario_daten):
    wach = mit(szenario_daten, SELBST, rd_reaktion=WACH, rd_atmung="ja-normale-atmung")
    assert meldungen(graph, wach) == []
    unklar = mit(szenario_daten, SELBST, rd_reaktion=WACH, rd_atmung="unbekannt")
    assert "1. Hand, aber nicht wach, nicht atmend oder Zustand unbekannt" in meldungen(
        graph, unklar
    )


def test_ein_stillstand_braucht_die_zweite_hand_vor_ort(graph, szenario_daten):
    meldung = "Stillstand oder Todeszeichen, aber Anrufer nicht 2. Hand vor Ort"
    dabei = mit(szenario_daten, rd_atmung="atmet-nicht", rd_reaktion="reagiert-nicht")
    assert meldung not in meldungen(graph, dabei)
    fern = mit(szenario_daten, FUER_ANDERE, NICHT_DA, rd_atmung="atmet-nicht")
    assert meldung in meldungen(graph, fern)


def test_strassenlagen_haben_kein_geschoss(graph, szenario_daten):
    endpunkt = next(e for e in graph.endpunkte if e.protokoll == "rd.29" and e.pfad)
    antworten = {s.knoten: {"antwort": s.antwort} for s in endpunkt.pfad}
    daten = {
        **szenario_daten,
        "antworten": {**antworten, "eroeffnung.hand": {"antwort": BEIM_BETROFFENEN}},
        "ziel": {"knoten": endpunkt.knoten, "code": endpunkt.code},
    }
    gemeldet = meldungen(graph, Szenario.model_validate(daten))
    assert "Geschoss oder Klingel bei einer Lage auf der Straße oder am Wasser" in gemeldet


def test_automatisch_meldet_nur_eine_anlage(graph, szenario_daten):
    gemeldet = meldungen(graph, mit(szenario_daten, AUTOMATISCH, NICHT_DA))
    assert "automatische Meldung bei einer Lage, die keine Anlage meldet" in gemeldet


def test_ohne_adresse_und_tafel_nur_vor_ort(graph, szenario_daten):
    daten = {
        **szenario_daten,
        "ort": {
            "adresse": {"ortsteil": "Neukölln"},
            "koordinaten": [52.48, 13.41],
            "ohneAdresse": {"wo": "ein Park", "umgebung": []},
        },
    }
    daten["antworten"] = {
        **daten["antworten"],
        "eroeffnung.hand": {"antwort": FUER_ANDERE},
        "eroeffnung.vor-ort": {"antwort": NICHT_DA},
    }
    gemeldet = meldungen(graph, Szenario.model_validate(daten))
    assert "Anrufer ohne Adresse beschreibt die Umgebung, ist aber nicht vor Ort" in gemeldet


def test_die_pruefung_zeigt_sie_als_warnungen(graph, szenario_daten):
    befunde = pruefen(mit(szenario_daten, GEHOERT), graph)
    stimmigkeit = [b for b in befunde if "vor Ort" in b.meldung]
    assert stimmigkeit
    assert all(b.art == "warnung" for b in stimmigkeit)


ADRESSE = {
    "strasse": "Karl-Marx-Straße",
    "hausnummer": "92",
    "plz": "12043",
    "ortsteil": "Neukölln",
    "breite": 52.47,
    "laenge": 13.43,
}


STRASSE = "Geschoss oder Klingel bei einer Lage auf der Straße oder am Wasser"


def generierte_meldungen(graph, anzahl=400):
    quellen = Quellen(adresse=lambda *_: dict(ADRESSE), ort=lambda *_: None)
    return [
        meldung
        for i in range(anzahl)
        for meldung in stimmigkeitsmeldungen(
            graph, generieren(graph, quellen, Erzeugung(), random.Random(i))
        )
    ]


def test_der_generator_erzeugt_stimmige_szenarien(graph):
    assert [m for m in generierte_meldungen(graph) if m != STRASSE] == []


@pytest.mark.xfail(strict=True, reason="Strassenlagen haben noch Geschoss und Klingel")
def test_der_generator_gibt_strassenlagen_kein_geschoss(graph):
    assert STRASSE not in generierte_meldungen(graph)


def am_code(graph, szenario_daten, code, hand, vor_ort=VOR_ORT_JA, **mehr):
    endpunkt = next(e for e in graph.endpunkte if e.code == code)
    antworten = {s.knoten: {"antwort": s.antwort} for s in endpunkt.pfad}
    antworten.update(
        {
            "eroeffnung.hand": {"antwort": hand},
            "eroeffnung.vor-ort": {"antwort": vor_ort},
            **mehr,
        }
    )
    daten = {
        **szenario_daten,
        "ort": {**szenario_daten["ort"], "geschoss": "", "klingel": ""},
        "antworten": antworten,
        "ziel": {"knoten": endpunkt.knoten, "code": endpunkt.code},
    }
    return Szenario.model_validate(daten)


def test_eingeklemmte_rufen_nicht_selbst_an(graph, szenario_daten):
    meldung = "1. Hand bei einer Lage, in der niemand selbst anruft"
    assert meldung in meldungen(graph, am_code(graph, szenario_daten, "22B01M", SELBST))
    dabei = am_code(graph, szenario_daten, "22B01M", BEIM_BETROFFENEN)
    assert meldung not in meldungen(graph, dabei)


def test_der_code_bestimmt_die_hand_mit(graph, szenario_daten):
    selbst = "der Code nennt einen Anrufer 1. Hand, die Eröffnung nicht"
    assert selbst in meldungen(graph, am_code(graph, szenario_daten, "29A01", BEIM_BETROFFENEN))
    assert selbst not in meldungen(graph, am_code(graph, szenario_daten, "29A01", SELBST))
    nah = "der Code nennt einen Anrufer 1. oder 2. Hand, die Eröffnung nicht"
    fern = am_code(graph, szenario_daten, "29B04", FUER_ANDERE, NICHT_DA)
    assert nah in meldungen(graph, fern)
    assert nah not in meldungen(graph, am_code(graph, szenario_daten, "29B04", BEIM_BETROFFENEN))


def test_niemand_vor_ort_heisst_nicht_vor_ort(graph, szenario_daten):
    meldung = "der Code sagt, niemand ist vor Ort, die Eröffnung sagt vor Ort"
    vor_ort = am_code(graph, szenario_daten, "29A02", BEIM_BETROFFENEN)
    assert meldung in meldungen(graph, vor_ort)
    fern = am_code(graph, szenario_daten, "29A02", FUER_ANDERE, NICHT_DA)
    assert meldung not in meldungen(graph, fern)


def test_eine_tafel_liest_nur_wer_vor_ort_ist(graph, szenario_daten):
    meldung = "Warntafel gelesen, aber Anrufer nicht vor Ort"
    tafel = {"fw.th.verkehrsunfall.warntafel": {"wert": "33/1203"}}
    endpunkt = next(
        e
        for e in graph.endpunkte
        if any(s.knoten == "fw.th.verkehrsunfall.warntafel" for s in e.pfad)
    )
    fern = am_code(graph, szenario_daten, endpunkt.code, FUER_ANDERE, NICHT_DA, **tafel)
    assert meldung in meldungen(graph, fern)
    nah = am_code(graph, szenario_daten, endpunkt.code, BEIM_BETROFFENEN, **tafel)
    assert meldung not in meldungen(graph, nah)


def test_wer_selbst_anruft_reagiert_und_ist_kein_kind(graph, szenario_daten):
    meldung = "1. Hand, aber nicht wach, nicht atmend oder Zustand unbekannt"
    bewusstlos = mit(szenario_daten, SELBST, rd_reaktion="reagiert-nicht")
    assert meldung in meldungen(graph, bewusstlos)
    kind = Szenario.model_validate(
        {
            **szenario_daten,
            "antworten": {
                **mit(szenario_daten, SELBST).model_dump(by_alias=True)["antworten"],
                "rd.alter": {"wert": "9"},
            },
        }
    )
    assert "1. Hand bei einer Lage, in der niemand selbst anruft" in meldungen(graph, kind)


def test_monate_zaehlen_als_kind(graph, szenario_daten):
    kind = Szenario.model_validate(
        {
            **szenario_daten,
            "antworten": {
                **mit(szenario_daten, SELBST).model_dump(by_alias=True)["antworten"],
                "rd.alter": {"wert": "18 Monate"},
            },
        }
    )
    assert "1. Hand bei einer Lage, in der niemand selbst anruft" in meldungen(graph, kind)
