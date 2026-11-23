import random
from collections import Counter

import pytest

from gefahrstoffe import GEFAHRGUT_ANTWORTEN, Stoff
from szenario import Gefahrgut, Wahl, pruefen
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
    mit_gefahrgut,
    person_ziehen,
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


def test_stillstaende_kommen_nur_ueber_atmet_nicht_zu_09e01(graph):
    szenarien = viele(graph, 300, Erzeugung(kategorie="RD1NC"))
    stillstand = [s for s in szenarien if s.antworten["rd.atmung"].antwort == "atmet-nicht"]
    assert stillstand
    assert {s.ziel.code[:5] for s in stillstand} <= {"09E01", "09B01"}
    assert "09E01" in {s.ziel.code for s in stillstand}
    assert all("rd.hauptbeschwerde" not in s.antworten for s in stillstand)
    assert all(
        s.ziel.code.startswith("09B01")
        for s in viele(graph, 200, Erzeugung(kategorie="RD5."))
        if s.antworten["rd.atmung"].antwort == "atmet-nicht"
    )


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


def test_ein_anteil_der_szenarien_spielt_an_orten_mit_naechster_tuer(graph):
    gefragt = []

    def ort(_, ortsteil="", arten=()):
        gefragt.append(arten)
        return {**PLATZ, "name": "U Hermannplatz", "art": "Bahnhof"}

    quellen = Quellen(adresse=lambda *_: dict(ADRESSE), ort=ort, naechste=lambda *_: dict(ADRESSE))
    am_platz = viele(graph, 20, Erzeugung(anteil_orte=100), quellen=quellen)
    assert {s.ort.objekt for s in am_platz} == {"U Hermannplatz (Bahnhof)"}
    assert {s.ort.adresse.strasse for s in am_platz} == {"Karl-Marx-Straße"}
    assert {s.ort.koordinaten for s in am_platz} == {(52.47, 13.4)}
    assert all(s.ort.geschoss == "" for s in am_platz)
    assert "Supermarkt" in gefragt[0] and "Fluss" not in gefragt[0]
    assert all(
        s.ort.objekt == "" for s in viele(graph, 20, Erzeugung(anteil_orte=0), quellen=quellen)
    )


def test_ein_ort_ausserhalb_des_bezirks_wird_nicht_genommen(graph):
    quellen = Quellen(
        adresse=lambda *_: dict(ADRESSE),
        ort=lambda *_: dict(PLATZ, art="Park"),
        naechste=lambda *_: dict(ADRESSE, bezirk="Spandau"),
    )
    szenario = viele(graph, 1, Erzeugung(anteil_orte=100, bezirk="Neukölln"), quellen=quellen)[0]
    assert szenario.ort.objekt == ""


def test_neugeborene_sind_unter_den_stillstaenden_selten(graph):
    endpunkte = {e.knoten: e for e in graph.endpunkte}
    stillstand = [
        s for s in viele(graph, 600, Erzeugung(kategorie="RD1NC")) if s.ziel.code == "09E01"
    ]
    neugeboren = sum("NNAD" in endpunkte[s.ziel.knoten].kategorie for s in stillstand)
    assert stillstand
    assert neugeboren / len(stillstand) < 0.15


def test_sichere_todeszeichen_werden_ueber_atmet_nicht_gezogen(graph):
    tot = viele(graph, 300, Erzeugung(kategorie="RD5."))
    am_ende = [s for s in tot if s.ziel.code.startswith("09B01")]
    assert am_ende
    assert all(s.antworten["rd.atmung"].antwort == "atmet-nicht" for s in am_ende)
    assert all("rd.09.todeszeichen" in s.antworten for s in am_ende)


def test_varianten_eines_codes_teilen_sich_seine_chance(graph):
    from szenariogenerator import gewichte_der_codes

    neunzehn = [
        e for e in graph.endpunkte if e.protokoll == "rd.09" and e.pfad[0].knoten == "rd.atmung"
    ]
    gewichte = dict(zip([e.knoten for e in neunzehn], gewichte_der_codes(neunzehn), strict=True))
    tod = sum(g for k, g in gewichte.items() if "09b01" in k)
    stillstand = sum(g for k, g in gewichte.items() if "09e01" in k)
    assert tod == pytest.approx(1.0)
    assert stillstand == pytest.approx(1.0)
    assert gewichte["rd.09.09e01-2"] < gewichte["rd.09.09e01"] / 5


def test_das_geschlecht_folgt_geschlechtsbezogenen_antworten(graph):
    maenner = [
        e
        for e in graph.endpunkte
        if any(
            (a := graph.antwort(s.knoten, s.antwort or "")) and a.geschlecht == "m" for s in e.pfad
        )
    ]
    assert maenner
    zufall = random.Random(3)
    for endpunkt in maenner[:5]:
        person = person_ziehen(graph, endpunkt, zufall)
        assert person.weiblich is False


def test_ein_pfad_mit_unbekanntem_alter_laesst_das_alter_leer(graph):
    unbekannt = [
        s
        for s in viele(graph, 400)
        if any(
            (a := graph.antwort(k, w.antwort or "")) and a.alter and a.alter.unbekannt
            for k, w in s.antworten.items()
        )
    ]
    assert unbekannt
    assert all(s.antworten["rd.alter"].wert is None for s in unbekannt if "rd.alter" in s.antworten)


def test_frauenantworten_geben_eine_frau(graph):
    frauen = [
        e
        for e in graph.endpunkte
        if any(
            (a := graph.antwort(s.knoten, s.antwort or "")) and a.geschlecht == "w" for s in e.pfad
        )
    ]
    assert frauen
    for endpunkt in frauen:
        person = person_ziehen(graph, endpunkt, random.Random(1))
        assert person.weiblich is True
        assert 12 <= person.alter <= 50 or endpunkt.protokoll != "rd.31"


def test_gleichwertige_antworten_werden_gestreut(graph):
    brand = viele(graph, 300, Erzeugung(gewicht_rd=0, gewicht_th=0, gewicht_brand=1))
    flucht = "fw.brand.gebaeudebrand.fluchtweg"
    mit = [s for s in brand if flucht in s.antworten]
    wege = {s.antworten[flucht].antwort for s in mit}
    assert {"weg-frei", "weg-verraucht"} <= wege
    for szenario in mit:
        if szenario.antworten["eroeffnung.vor-ort"].antwort != "ja-der-anrufer-ist-vor-ort":
            assert szenario.antworten[flucht].antwort == "nicht-im-gebaeude"


def test_antworten_die_den_weg_bestimmen_bleiben_wie_im_pfad(graph):
    endpunkte = {e.knoten: e for e in graph.endpunkte}
    for szenario in viele(graph, 300):
        endpunkt = endpunkte[szenario.ziel.knoten]
        for schritt in endpunkt.pfad:
            ziele = {a.ziel for a in graph.knoten[schritt.knoten].antworten or []}
            if len(ziele) > 1:
                assert szenario.antworten[schritt.knoten].antwort == schritt.antwort


def test_gefahrgut_szenarien_tragen_eine_warntafel(graph):
    stoff = Stoff(un="1203", gefahrenzahl="33", klasse="3", bezeichnung="Benzin")
    quellen = Quellen(
        adresse=lambda *_: dict(ADRESSE), ort=lambda *_: dict(PLATZ), gefahrstoffe=[stoff]
    )
    nur_fw = Erzeugung(gewicht_rd=0, gewicht_brand=50, gewicht_th=50)
    endpunkte = {endpunkt.knoten: endpunkt for endpunkt in graph.endpunkte}
    mit_tafel = 0
    for seed in range(300):
        szenario = generieren(graph, quellen, nur_fw, random.Random(seed))
        erwartet = endpunkte[szenario.ziel.knoten].protokoll == "fw.th.gefahrstoffe" or any(
            (knoten, wahl.antwort) in GEFAHRGUT_ANTWORTEN
            for knoten, wahl in szenario.antworten.items()
        )
        assert (szenario.ort.gefahrgut is not None) == erwartet
        if erwartet:
            assert szenario.ort.gefahrgut == Gefahrgut(un="1203", gefahrenzahl="33")
            mit_tafel += 1
    assert mit_tafel > 0


def test_gefahrgut_im_rettungsdienst_bekommt_keine_tafel(graph):
    endpunkt = next(e for e in graph.endpunkte if e.protokoll == "rd.29")
    antworten = {"rd.29.k0": Wahl(antwort="gefahrgut")}
    assert not mit_gefahrgut(endpunkt, antworten)
