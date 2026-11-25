import json
import random
import re

import pytest

import beschwerden
from einstellungen import einstellungen
from meldehand import BEIM_BETROFFENEN, SELBST, VOR_ORT_JA, WACH
from stimmigkeit import alter_aus, pfadtext
from szenario import Wahl
from szenariogenerator import BELASTENDE, Erzeugung, Quellen, generieren

ADRESSE = {
    "strasse": "Karl-Marx-Straße",
    "hausnummer": "92",
    "plz": "12043",
    "ortsteil": "Neukölln",
    "bezirk": "Neukölln",
    "breite": 52.48,
    "laenge": 13.44,
}


def vor_ort_antwort(antworten) -> str:
    """Return where the caller is; unasked, as for a medical caller who is the patient, on site."""
    wahl = antworten.get("eroeffnung.vor-ort")
    return wahl.antwort if wahl is not None else "ja-der-anrufer-ist-vor-ort"


@pytest.fixture(scope="module")
def katalog(graph):
    return beschwerden.laden(einstellungen().beschwerden_verzeichnis, graph)


def lage(**mehr):
    return {
        "id": "x",
        "protokolle": ["rd.28"],
        "selbst": ["Mir ist schwindlig."],
        "beobachtet": [],
        **mehr,
    }


def geladen(tmp_path, graph, *lagen):
    (tmp_path / "a.json").write_text(json.dumps({"lagen": list(lagen)}), "utf-8")
    return beschwerden.laden(tmp_path, graph)


def test_der_mitgelieferte_katalog_passt_zum_graphen(katalog):
    ids = {lage.id for lage in katalog}
    assert {"stillstand", "schlaganfall", "brustschmerz", "atemnot", "wehen"} <= ids
    for eintrag in katalog:
        assert len(eintrag.beobachtet) >= 3
        assert not eintrag.selbst or len(eintrag.selbst) >= 3


@pytest.mark.parametrize(
    ("eintrag", "meldung"),
    [
        (lage(protokolle=["rd.99"]), "Protokoll rd.99 gibt es nicht"),
        (lage(codes=["99Z"]), "kein Code beginnt mit 99Z"),
        (lage(selbst=[]), "ohne Beschwerden"),
        (lage(selbst=["{Sie} hustet."]), "unbekannter Platzhalter {Sie}"),
        (lage(protokolle=[]), "ohne Protokoll"),
    ],
)
def test_ein_fehlerhafter_katalog_haelt_den_start_auf(tmp_path, graph, eintrag, meldung):
    with pytest.raises(ValueError, match=meldung.replace("{", r"\{").replace("}", r"\}")):
        geladen(tmp_path, graph, eintrag)


def test_doppelte_ids_fallen_auf(tmp_path, graph):
    with pytest.raises(ValueError, match="x: gibt es doppelt"):
        geladen(tmp_path, graph, lage(), lage())


def test_eine_lage_mit_codes_geht_vor(tmp_path, graph):
    endpunkt = next(e for e in graph.endpunkte if e.protokoll == "rd.28")
    lagen = geladen(tmp_path, graph, lage(id="ganz"), lage(id="eng", codes=[endpunkt.code[:3]]))
    assert beschwerden.lage_fuer(lagen, endpunkt, "", 50).id == "eng"


def test_eine_lage_gilt_nur_im_altersbereich(tmp_path, graph):
    endpunkt = next(e for e in graph.endpunkte if e.protokoll == "rd.28")
    lagen = geladen(tmp_path, graph, lage(alter=[13, 120]))
    assert beschwerden.lage_fuer(lagen, endpunkt, "", 50) is not None
    assert beschwerden.lage_fuer(lagen, endpunkt, "", 4) is None


@pytest.mark.parametrize(
    ("eintrag", "meldung"),
    [
        (lage(wenn=["gibt es nirgends"]), "Muster gibt es nirgends passt auf keinen Pfad"),
        (lage(nicht=["(offen"]), r"Muster \(offen ist ungültig"),
        (lage(selbst=[{"text": "x", "codes": ["99Z"]}]), "„x“: kein Code beginnt mit 99Z"),
    ],
)
def test_muster_und_codes_muessen_einen_pfad_treffen(tmp_path, graph, eintrag, meldung):
    with pytest.raises(ValueError, match=meldung):
        geladen(tmp_path, graph, eintrag)


def test_eine_beschwerde_widerspricht_der_eroeffnung_nicht():
    getruebt = beschwerden.Beschwerde(text="x", zeigt=["eingetruebt"])
    wach = beschwerden.Beschwerde(text="x", zeigt=["wach"])
    luft = beschwerden.Beschwerde(text="x", zeigt=["atemnot"])
    assert not getruebt.stimmt(WACH, None)
    assert getruebt.stimmt("reagiert-aber-nicht-normal", None)
    assert not wach.stimmt("reagiert-nicht", None)
    assert wach.stimmt(WACH, None)
    assert not luft.stimmt(None, "ja-normale-atmung")
    assert luft.stimmt(None, "atmung-auffaellig")
    reagiert = beschwerden.Beschwerde(text="x", zeigt=["reagiert"])
    assert not reagiert.stimmt("reagiert-nicht", None)
    assert reagiert.stimmt("reagiert-aber-nicht-normal", None)


def test_die_pronomen_folgen_dem_geschlecht():
    text = "{Er} reagiert nicht, wenn ich {ihn} schüttle, und {er} gibt {ihm} keine Antwort."
    assert beschwerden.gefuellt(text, False) == (
        "Er reagiert nicht, wenn ich ihn schüttle, und er gibt ihm keine Antwort."
    )
    assert beschwerden.gefuellt(text, True) == (
        "Sie reagiert nicht, wenn ich sie schüttle, und sie gibt ihr keine Antwort."
    )


def herkunft(katalog):
    woher = {}
    for eintrag in katalog:
        for sicht, liste in (("selbst", eintrag.selbst), ("beobachtet", eintrag.beobachtet)):
            for b in liste:
                for weiblich in (False, True):
                    woher.setdefault(beschwerden.gefuellt(b.text, weiblich), []).append(
                        (eintrag, b, sicht)
                    )
    return woher


OHNE_BESCHWERDEN = {"rd.34", "rd.39"}
ANSPRECHBAR = re.compile(r"\b(sagt|redet|hält|schreit|spricht|wach|versteht|krümmt|hustet)\b")
ALLE_BELASTENDEN = sorted(BELASTENDE)


def rd_protokolle(graph):
    return sorted(
        {e.protokoll for e in graph.endpunkte if e.protokoll.startswith("rd.")} - OHNE_BESCHWERDEN
    )


def test_jede_lage_der_notfallrettung_hat_beschwerden(graph, katalog):
    abgedeckt = {protokoll for eintrag in katalog for protokoll in eintrag.protokolle}
    assert set(rd_protokolle(graph)) <= abgedeckt


def test_gezogene_beschwerden_passen_zu_pfad_eroeffnung_und_sicht(graph, katalog):
    quellen = Quellen(adresse=lambda *_: dict(ADRESSE), ort=lambda *_: None, beschwerden=katalog)
    zufall = random.Random(5)
    woher = herkunft(katalog)
    endpunkte = {e.knoten: e for e in graph.endpunkte}
    gesehen = set()
    for protokoll in rd_protokolle(graph):
        for _ in range(60):
            szenario = generieren(
                graph,
                quellen,
                Erzeugung(protokoll=protokoll, anteil_orte=0, belastende=ALLE_BELASTENDEN),
                zufall,
            )
            endpunkt = endpunkte[szenario.ziel.knoten]
            text = pfadtext(graph, endpunkt)
            antworten = szenario.antworten
            gezogen = szenario.rolle.beschwerden
            hand = antworten["eroeffnung.hand"].antwort
            vor_ort = vor_ort_antwort(antworten) == VOR_ORT_JA
            alter = alter_aus(antworten["rd.alter"].wert or "")
            if szenario.ziel.code.startswith("09B01") or not (
                hand == SELBST or (hand == BEIM_BETROFFENEN and vor_ort)
            ):
                assert gezogen == []
                continue
            assert len(gezogen) <= 3
            reaktion = (antworten.get("rd.reaktion") or Wahl()).antwort
            atmung = (antworten.get("rd.atmung") or Wahl()).antwort
            sicht_soll = "selbst" if hand == SELBST else "beobachtet"
            for satz in gezogen:
                moeglich = [
                    (eintrag, beschwerde)
                    for eintrag, beschwerde, sicht in woher[satz]
                    if sicht == sicht_soll
                    and endpunkt.protokoll in eintrag.protokolle
                    and eintrag.passt(endpunkt, text)
                    and (alter is None or eintrag.alter[0] <= alter <= eintrag.alter[1])
                    and beschwerde.passt(endpunkt, text)
                    and beschwerde.stimmt(reaktion, atmung)
                ]
                assert moeglich, (satz, endpunkt.code, reaktion, atmung)
                if reaktion == "reagiert-nicht":
                    assert not ANSPRECHBAR.search(satz), (satz, endpunkt.code)
                gesehen.add(moeglich[0][0].id)
            if alter is not None and alter <= 12 and protokoll == "rd.09":
                assert not any("Schultern" in satz or "umgekippt" in satz for satz in gezogen)
    assert {"stillstand", "stillstand-kind", "schlaganfall", "wehen", "sturz"} <= gesehen


def test_ohne_katalog_bleiben_die_beschwerden_leer(graph):
    quellen = Quellen(adresse=lambda *_: dict(ADRESSE), ort=lambda *_: None)
    szenario = generieren(graph, quellen, Erzeugung(protokoll="rd.28"), random.Random(1))
    assert szenario.rolle.beschwerden == []
