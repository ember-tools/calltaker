import random
from collections import Counter

import pytest

from szenario import pruefen
from szenariogenerator import (
    ATEMNOT,
    BEWUSSTLOS,
    SELBST,
    STILLSTAND,
    VOR_ORT,
    Erzeugung,
    NichtsZuZiehen,
    Quellen,
    altersspanne,
    anzahl_gewichte,
    disziplin_von,
    generieren,
    pfadtext,
    stufe,
    titel_von,
)

ADRESSE = {
    "strasse": "Karl-Marx-Straße",
    "hausnummer": "92",
    "plz": "12043",
    "ortsteil": "Neukölln",
    "bezirk": "Neukölln",
    "breite": 52.48,
    "laenge": 13.44,
}
PLATZ = {"name": "Tempelhofer Feld", "ortsteil": "Tempelhof", "breite": 52.47, "laenge": 13.4}
QUELLEN = Quellen(adresse=lambda *_: dict(ADRESSE), ort=lambda *_: dict(PLATZ))


def viele(graph, anzahl=400, erzeugung=None, quellen=QUELLEN, saat=7):
    zufall = random.Random(saat)
    return [generieren(graph, quellen, erzeugung or Erzeugung(), zufall) for _ in range(anzahl)]


def test_generierte_szenarien_passen_zum_graphen(graph):
    for szenario in viele(graph):
        assert [b for b in pruefen(szenario, graph) if b.art == "fehler"] == []
        assert szenario.herkunft == "generiert"
        assert szenario.abfrage_version == graph.meta.version
        assert szenario.titel.endswith(", Neukölln")


def test_die_eroeffnung_widerspricht_dem_code_nicht(graph):
    endpunkte = {e.knoten: e for e in graph.endpunkte}
    for szenario in viele(graph, 1500):
        endpunkt = endpunkte[szenario.ziel.knoten]
        antworten = szenario.antworten
        if "rd.reaktion" not in antworten:
            continue
        reaktion = antworten["rd.reaktion"].antwort
        atmung = antworten["rd.atmung"].antwort
        text = pfadtext(graph, endpunkt)
        if endpunkt.protokoll == "rd.09" or STILLSTAND.search(text):
            assert (reaktion, atmung) == ("reagiert-nicht", "atmet-nicht"), endpunkt.code
        elif BEWUSSTLOS.search(text):
            assert reaktion != "ja-wach-und-ansprechbar", endpunkt.code
        elif endpunkt.kategorie.startswith(("RD4", "RD5")) and not ATEMNOT.search(text):
            assert (reaktion, atmung) == ("ja-wach-und-ansprechbar", "ja-normale-atmung")
        stillstand = (
            endpunkt.protokoll == "rd.09"
            or endpunkt.kategorie.startswith("RD1NC REA")
            or STILLSTAND.search(text)
        )
        if ATEMNOT.search(text) and not stillstand:
            assert atmung == "atmung-auffaellig", endpunkt.code
        if antworten["eroeffnung.hand"].antwort == SELBST:
            assert reaktion == "ja-wach-und-ansprechbar"


def test_meldehand_und_vor_ort_passen_zusammen(graph):
    for szenario in viele(graph, 800):
        hand = szenario.antworten["eroeffnung.hand"].antwort
        vor_ort = szenario.antworten["eroeffnung.vor-ort"].antwort
        assert vor_ort in VOR_ORT[hand]


def test_tote_personen_im_protokoll_09_atmen_nicht(graph):
    tote = Erzeugung(kategorie="RD5.")
    endpunkte = {e.knoten: e for e in graph.endpunkte}
    gesehen = 0
    for szenario in viele(graph, 400, tote):
        if endpunkte[szenario.ziel.knoten].protokoll == "rd.09":
            gesehen += 1
            assert szenario.antworten["rd.atmung"].antwort == "atmet-nicht"
    assert gesehen > 0


def test_titel_ohne_eigenen_anlass_nennen_das_protokoll(graph):
    endpunkt = next(e for e in graph.endpunkte if e.anlass == e.code)
    assert titel_von(graph, endpunkt).endswith(f"({endpunkt.code})")
    assert titel_von(graph, endpunkt) != endpunkt.code


def test_stufen_fuer_sonderkategorien():
    assert [
        stufe(k)
        for k in ("RD_Mehrere Patienten", "RD_BT_RTW", "BRAND M.", "TH K.", "RD1NC REA.", "BRAND 8")
    ] == [1, 3, 3, 4, 1, 1]


def test_disziplinen_nach_gewicht_und_kategoriefilter(graph):
    nur_th = Erzeugung(gewicht_rd=0, gewicht_brand=0, gewicht_th=1)
    endpunkte = {e.knoten: e for e in graph.endpunkte}
    assert {disziplin_von(endpunkte[s.ziel.knoten]) for s in viele(graph, 50, nur_th)} == {"th"}
    rea = Erzeugung(kategorie="RD1NC REA")
    assert all(
        graph.knoten[s.ziel.knoten].kategorie.startswith("RD1NC REA") for s in viele(graph, 50, rea)
    )
    with pytest.raises(NichtsZuZiehen):
        viele(graph, 1, Erzeugung(kategorie="GIBTESNICHT"))


def test_das_alter_passt_zu_den_grenzen_des_pfads(graph):
    kinder = [e for e in graph.endpunkte if altersspanne(graph, e)[1] <= 12]
    assert kinder
    for endpunkt in kinder[:30]:
        unten, oben = altersspanne(graph, endpunkt)
        assert 0 <= unten <= oben <= 12


def test_rufnummern_unterdrueckt_und_abweichend(graph):
    szenarien = viele(graph, 2000)
    unterdrueckt = sum(s.anrufer.rufnummer_unterdrueckt for s in szenarien)
    anders = sum(bool(s.anrufer.rufnummer and s.anrufer.rueckrufnummer) for s in szenarien)
    assert 50 <= unterdrueckt <= 150
    assert 50 <= anders <= 150
    assert all(s.anrufer.rueckrufnummer for s in szenarien if s.anrufer.rufnummer_unterdrueckt)


def test_ohne_adressen_kommen_orte_und_ohne_beides_nichts(graph):
    nur_orte = Quellen(adresse=lambda *_: None, ort=lambda *_: dict(PLATZ))
    szenario = viele(graph, 1, quellen=nur_orte)[0]
    assert szenario.ort.objekt == "Tempelhofer Feld"
    assert szenario.ort.adresse.ortsteil == "Tempelhof"
    keine = Quellen(adresse=lambda *_: None, ort=lambda *_: None)
    with pytest.raises(NichtsZuZiehen, match="Weder"):
        viele(graph, 1, quellen=keine)
    with pytest.raises(NichtsZuZiehen, match="Gebiet"):
        viele(graph, 1, Erzeugung(ortsteil="Atlantis"), quellen=keine)


def test_stimmungen_folgen_der_dringlichkeit(graph):
    stimmungen = Counter(
        s.rolle.stimmung for s in viele(graph, 300, Erzeugung(kategorie="RD1NC REA"))
    )
    assert "ruhig" not in stimmungen
    assert stimmungen["panisch"] > 0


@pytest.mark.parametrize(
    ("anlass", "erwartet"),
    [
        ("Verkehrsunfall, 2 Verletzte", {"zwei-personen"}),
        ("Vergiftung, mehr als 4 Patienten", {"drei-oder-mehr"}),
        ("Verkehrsunfall mit mehr als 1 Verletzte", {"zwei-personen"}),
        ("Verkehrsunfall mit mehreren eingeklemmten Personen", {"zwei-personen", "drei-oder-mehr"}),
        ("Sturz", {"eine-person", "zwei-personen"}),
        ("Eingeklemmte Person und eine verletzte Person", {"drei-oder-mehr"}),
    ],
)
def test_die_anzahl_folgt_dem_anlass(graph, anlass, erwartet):
    kategorie = "RD_Mehrere Patienten" if anlass.startswith("Eingeklemmte") else "RD2NC."
    endpunkt = graph.endpunkte[0].model_copy(update={"anlass": anlass, "kategorie": kategorie})
    assert set(anzahl_gewichte(endpunkt)) == erwartet
