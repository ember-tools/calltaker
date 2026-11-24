import random
import re
from collections import Counter

import pytest

from gefahrstoffe import Stoff
from geo import entfernung
from stimmigkeit import BEIM_BETROFFENEN, FUER_ANDERE, GEHOERT, VOR_ORT_JA, alter_aus
from szenario import Szenario, Wahl, pruefen
from szenariogenerator import (
    AM_WASSER,
    ATEMNOT,
    BELASTENDE,
    BETRIEBE,
    BEWUSSTLOS,
    DRAUSSEN_ARTEN_FUER,
    DRAUSSEN_PROTOKOLLE,
    DRAUSSEN_VERSATZ,
    EINRICHTUNGEN,
    NEUGEBORENES,
    OEFFENTLICH_FUER,
    RAHMEN_JE_ART,
    SCHWANGER,
    SELBST,
    STILLSTAND,
    STRASSENSTELLEN,
    VOR_ORT,
    WOHNUNGSPROTOKOLLE,
    Erzeugung,
    NichtsZuZiehen,
    Person,
    Quellen,
    altersspanne,
    anzahl_gewichte,
    belastungen,
    disziplin_von,
    generieren,
    geschaetztes_alter,
    gleichwertige,
    himmelsrichtung,
    person_ziehen,
    pfadtext,
    stufe,
    titel_von,
    warntafel_ziehen,
    ziehbare,
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
    standard = Erzeugung(anteil_ohne_adresse=0)
    return [generieren(graph, quellen, erzeugung or standard, zufall) for _ in range(anzahl)]


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
        nicht_dabei = antworten["eroeffnung.hand"].antwort in (FUER_ANDERE, GEHOERT)
        if ATEMNOT.search(text) and not stillstand:
            erlaubt = ("atmung-auffaellig", "unbekannt") if nicht_dabei else ("atmung-auffaellig",)
            assert atmung in erlaubt, endpunkt.code
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
    nur_rd = {"protokoll": "rd.10", "anteil_ohne_adresse": 0}
    am_platz = viele(graph, 20, Erzeugung(anteil_orte=100, **nur_rd), quellen=quellen)
    assert {s.ort.objekt for s in am_platz} == {"U Hermannplatz (Bahnhof)"}
    assert {s.ort.adresse.strasse for s in am_platz} == {"Karl-Marx-Straße"}
    assert {s.ort.koordinaten for s in am_platz} == {(52.47, 13.4)}
    assert all(s.ort.geschoss == "" for s in am_platz)
    assert "Supermarkt" in gefragt[0] and "Fluss" not in gefragt[0]
    gefragt.clear()
    viele(graph, 40, Erzeugung(anteil_orte=0, **nur_rd), quellen=quellen)
    assert not any("Supermarkt" in arten for arten in gefragt)


def test_ein_ort_ausserhalb_des_bezirks_wird_nicht_genommen(graph):
    quellen = Quellen(
        adresse=lambda *_: dict(ADRESSE),
        ort=lambda *_: dict(PLATZ, art="Park"),
        naechste=lambda *_: dict(ADRESSE, bezirk="Spandau"),
    )
    szenario = viele(graph, 1, Erzeugung(anteil_orte=100, bezirk="Neukölln"), quellen=quellen)[0]
    assert "(Park)" not in szenario.ort.objekt


def test_neugeborene_sind_unter_den_stillstaenden_selten(graph):
    endpunkte = {e.knoten: e for e in graph.endpunkte}
    stillstand = [
        s for s in viele(graph, 2000, Erzeugung(kategorie="RD1NC")) if s.ziel.code == "09E01"
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
    assert tod / (tod + stillstand) == pytest.approx(0.05, abs=0.001)
    assert stillstand == pytest.approx(1.0)
    assert gewichte["rd.09.09e01-2"] < gewichte["rd.09.09e01"] / 5
    assert gewichte["rd.09.09b01e"] > gewichte["rd.09.09b01f"] > gewichte["rd.09.09b01b"]


def test_todeszeichen_sind_selten_und_ein_stillstand_hat_einen_hergang(graph):
    szenarien = viele(graph, 1500, Erzeugung(protokoll="rd.09", anteil_ohne_adresse=0))
    tot = [s for s in szenarien if s.ziel.code.startswith("09B01")]
    assert 0.02 <= len(tot) / len(szenarien) <= 0.09
    for szenario in tot:
        alter = int(szenario.antworten["rd.alter"].wert or 0)
        if szenario.ziel.code in ("09B01a", "09B01c", "09B01e"):
            assert alter >= 50
        assert szenario.rolle.stimmung != "panisch"
    stillstaende = [s for s in szenarien if s.ziel.code == "09E01"]
    assert {s.ziel.knoten for s in stillstaende} >= {"rd.09.09e01", "rd.09.09e01-3"}
    assert all(s.rolle.notizen for s in stillstaende)
    for szenario in stillstaende:
        if szenario.ziel.knoten != "rd.09.09e01-2":
            assert "Wenige Tage alt" not in szenario.rolle.notizen


def test_jeder_stillstand_hat_einen_hergang_auch_draussen(graph):
    quellen = Quellen(adresse=lambda *_: dict(ADRESSE), ort=lambda *_: dict(PLATZ))
    erzeugung = Erzeugung(protokoll="rd.09", anteil_orte=100)
    for i in range(400):
        szenario = generieren(graph, quellen, erzeugung, random.Random(i))
        if szenario.ziel.code == "09E01":
            assert szenario.rolle.notizen, szenario.ziel.knoten


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


def test_die_frage_nach_der_warntafel_beantwortet_der_generator(graph):
    stoff = Stoff(un="1203", gefahrenzahl="33", klasse="3", bezeichnung="Benzin")
    quellen = Quellen(
        adresse=lambda *_: dict(ADRESSE), ort=lambda *_: dict(PLATZ), gefahrstoffe=[stoff]
    )
    nur_fw = Erzeugung(gewicht_rd=0, gewicht_brand=50, gewicht_th=50)
    tafelfragen = {
        kid for kid, k in graph.knoten.items() if k.eingabe and k.eingabe.art == "warntafel"
    }
    gelesen = unlesbar = 0
    for seed in range(600):
        szenario = generieren(graph, quellen, nur_fw, random.Random(seed))
        vor_ort = szenario.antworten["eroeffnung.vor-ort"].antwort == "ja-der-anrufer-ist-vor-ort"
        for kid in tafelfragen & set(szenario.antworten):
            wert = szenario.antworten[kid].wert
            assert wert in ("33/1203", None)
            assert vor_ort or wert is None
            if vor_ort:
                gelesen += wert is not None
                unlesbar += wert is None
        assert not [b for b in pruefen(szenario, graph) if b.art == "fehler"]
    assert gelesen > unlesbar > 0
    ohne = Quellen(adresse=lambda *_: dict(ADRESSE), ort=lambda *_: dict(PLATZ))
    assert warntafel_ziehen(ohne, Person(40, True, False), random.Random(1)) == Wahl()


def test_wohnungen_haben_geschoss_klingel_und_manchmal_ein_haustier(graph):
    erzeugung = Erzeugung(
        gewicht_rd=34, gewicht_brand=33, gewicht_th=33, anteil_orte=0, anteil_ohne_adresse=0
    )
    endpunkte = {endpunkt.knoten: endpunkt for endpunkt in graph.endpunkte}
    mit_tier = wohnungen = 0
    gesehen = set()
    for seed in range(400):
        szenario = generieren(graph, QUELLEN, erzeugung, random.Random(seed))
        endpunkt = endpunkte[szenario.ziel.knoten]
        wohnung = endpunkt.fachrichtung == "rd" or endpunkt.protokoll in WOHNUNGSPROTOKOLLE
        if szenario.ort.geschoss:
            assert wohnung
            assert not szenario.ort.objekt
            wohnungen += 1
            gesehen.add(endpunkt.protokoll)
            person = szenario.betroffener.name if szenario.betroffener else szenario.anrufer.name
            assert szenario.ort.klingel == person.split()[-1]
            mit_tier += bool(szenario.ort.haustier)
        else:
            assert not szenario.ort.haustier
    assert wohnungen > 100
    assert 0 < mit_tier < wohnungen * 0.3
    assert gesehen & {"fw.th.tueroeffnung", "fw.th.wasserschaden"}


def test_wohnungsprotokolle_gibt_es_im_graphen(graph):
    protokolle = {endpunkt.protokoll for endpunkt in graph.endpunkte}
    assert WOHNUNGSPROTOKOLLE.issubset(protokolle)


def test_mobil_anrufer_bekommen_eine_funkzelle_um_den_wahren_punkt(graph):
    mit_zelle = 0
    for seed in range(200):
        szenario = generieren(graph, QUELLEN, Erzeugung(anteil_orte=0), random.Random(seed))
        anrufer = szenario.anrufer
        mobil = anrufer.mobil_angezeigt()
        wo = szenario.antworten["eroeffnung.vor-ort"].antwort
        assert (anrufer.funkzelle is not None) == (mobil and wo != "unbekannt")
        vor_ort = wo == VOR_ORT_JA
        if anrufer.funkzelle and vor_ort:
            mit_zelle += 1
            zelle = anrufer.funkzelle
            assert 500 <= zelle.radius <= 1500
            abstand = entfernung(zelle.mitte, szenario.ort.koordinaten)
            assert 90 <= abstand <= zelle.radius
    assert mit_zelle > 0


PARK = {
    "name": "Volkspark Hasenheide",
    "art": "Park",
    "ortsteil": "Neukölln",
    "breite": 52.484,
    "laenge": 13.414,
}
NAHE = [
    dict(PARK),
    {
        "name": "U Hermannplatz",
        "art": "Bahnhof",
        "ortsteil": "Neukölln",
        "breite": 52.4867,
        "laenge": 13.4244,
    },
    {
        "name": "Edeka",
        "art": "Supermarkt",
        "ortsteil": "Neukölln",
        "breite": 52.4825,
        "laenge": 13.4140,
    },
    {"name": "Edeka", "art": "Kiosk", "ortsteil": "Neukölln", "breite": 52.4825, "laenge": 13.4140},
    {
        "name": "Spielplatz Jahnstraße",
        "art": "Spielplatz",
        "ortsteil": "Neukölln",
        "breite": 52.4851,
        "laenge": 13.4105,
    },
]


def draussen_quellen(nahe, gefragt=None):
    def ort(_, ortsteil="", arten=()):
        if gefragt is not None:
            gefragt.append(set(arten))
        return dict(PARK)

    return Quellen(
        adresse=lambda *_: dict(ADRESSE), ort=ort, umkreis=lambda *_: [dict(o) for o in nahe]
    )


def test_anrufer_ohne_adresse_stehen_draussen_und_beschreiben_die_umgebung(graph):
    gefragt = []
    quellen = draussen_quellen(NAHE, gefragt)
    endpunkte = {endpunkt.knoten: endpunkt for endpunkt in graph.endpunkte}
    erzeugung = Erzeugung(
        anteil_ohne_adresse=100, anteil_orte=0, gewicht_rd=40, gewicht_brand=30, gewicht_th=30
    )
    szenarien = [generieren(graph, quellen, erzeugung, random.Random(i)) for i in range(300)]
    draussen = [s for s in szenarien if s.ort.ohne_adresse]
    assert draussen
    assert any(not s.ort.ohne_adresse for s in szenarien if s.anrufer.mobil_angezeigt())
    assert set(DRAUSSEN_ARTEN_FUER["rd"]) in gefragt
    for szenario in draussen:
        endpunkt = endpunkte[szenario.ziel.knoten]
        assert endpunkt.fachrichtung == "rd" or endpunkt.protokoll in DRAUSSEN_PROTOKOLLE
        assert szenario.anrufer.mobil_angezeigt()
        assert szenario.ort.adresse.strasse == ""
        assert szenario.ort.objekt == "Volkspark Hasenheide"
        assert 14 <= entfernung(szenario.ort.koordinaten, (52.484, 13.414)) <= 61
        ohne = szenario.ort.ohne_adresse
        assert ohne.wo in ("Volkspark Hasenheide", "ein Park")
        namen = [o.name for o in ohne.umgebung]
        assert 2 <= len(namen) <= 3
        assert len(set(namen)) == len(namen)
        assert "Volkspark Hasenheide" not in namen
        assert [o.meter for o in ohne.umgebung] == sorted(o.meter for o in ohne.umgebung)
        assert szenario.anrufer.funkzelle is not None
        assert not [b for b in pruefen(szenario, graph) if b.art == "fehler"]


def test_draussen_nur_mit_anteil_ohne_bezirk_und_mit_genug_umgebung(graph):
    def keiner(erzeugung, nahe=NAHE):
        quellen = draussen_quellen(nahe)
        return not any(
            generieren(graph, quellen, erzeugung, random.Random(i)).ort.ohne_adresse
            for i in range(150)
        )

    assert keiner(Erzeugung(anteil_ohne_adresse=0, anteil_orte=0))
    assert keiner(Erzeugung(anteil_ohne_adresse=100, anteil_orte=0, bezirk="Neukölln"))
    assert keiner(Erzeugung(anteil_ohne_adresse=100, anteil_orte=0), nahe=[dict(PARK), NAHE[1]])


def test_der_versatz_bleibt_unter_der_genauigkeit_des_punkts():
    assert DRAUSSEN_VERSATZ[1] < 75


def test_eine_adresse_verdraengt_die_beschreibung_ohne_adresse(szenario_daten):
    ohne = {"wo": "ein Park", "umgebung": []}
    daten = {**szenario_daten, "ort": {**szenario_daten["ort"], "ohneAdresse": ohne}}
    assert Szenario.model_validate(daten).ort.ohne_adresse is None
    draussen = {
        **daten,
        "ort": {**daten["ort"], "adresse": {"ortsteil": "Neukölln"}, "koordinaten": [52.48, 13.41]},
    }
    assert Szenario.model_validate(draussen).ort.ohne_adresse is not None


def test_himmelsrichtungen():
    mitte = (52.5, 13.4)
    assert himmelsrichtung(mitte, (52.51, 13.4)) == "Norden"
    assert himmelsrichtung(mitte, (52.5, 13.42)) == "Osten"
    assert himmelsrichtung(mitte, (52.49, 13.385)) == "Südwesten"


def test_eine_gewaehlte_lage_wird_unabhaengig_von_den_gewichten_gezogen(graph):
    nur_vu = Erzeugung(protokoll="fw.th.verkehrsunfall", gewicht_th=0, anteil_ohne_adresse=0)
    szenarien = viele(graph, 30, nur_vu)
    endpunkte = {e.knoten: e for e in graph.endpunkte}
    assert {endpunkte[s.ziel.knoten].protokoll for s in szenarien} == {"fw.th.verkehrsunfall"}
    with pytest.raises(NichtsZuZiehen):
        viele(graph, 1, Erzeugung(protokoll="gibt.es.nicht"))


def eroeffnungen(graph, erzeugung, anzahl=600):
    endpunkte = {e.knoten: e for e in graph.endpunkte}
    for szenario in viele(graph, anzahl, erzeugung):
        yield endpunkte[szenario.ziel.knoten], szenario


def test_stillstaende_haben_immer_die_zweite_hand_vor_ort(graph):
    gesehen = 0
    for _, szenario in eroeffnungen(
        graph, Erzeugung(kategorie="RD1NC", anteil_ohne_adresse=0), 300
    ):
        if szenario.antworten["rd.atmung"].antwort == "atmet-nicht":
            gesehen += 1
            assert (
                szenario.antworten["eroeffnung.hand"].antwort
                == "2-hand-der-anrufer-ist-beim-betroffenen"
            )
            assert szenario.antworten["eroeffnung.vor-ort"].antwort == "ja-der-anrufer-ist-vor-ort"
    assert gesehen


def test_die_erste_hand_kennt_ihre_atmung(graph):
    for _, szenario in eroeffnungen(graph, Erzeugung(gewicht_brand=0, gewicht_th=0)):
        if szenario.antworten["eroeffnung.hand"].antwort == SELBST:
            assert szenario.antworten["rd.atmung"].antwort in (
                "ja-normale-atmung",
                "atmung-auffaellig",
            )


def test_die_vierte_hand_kennt_kein_genaues_alter(graph):
    gesehen = 0
    for _, szenario in eroeffnungen(graph, Erzeugung(gewicht_brand=0, gewicht_th=0), 1500):
        if szenario.antworten["eroeffnung.hand"].antwort == "4-hand-der-anrufer-hat-es-nur-gehoert":
            gesehen += 1
            wert = szenario.antworten["rd.alter"].wert or ""
            assert wert == "" or wert.startswith("etwa ")
    assert gesehen


def test_feuerwehr_kennt_alle_haende_und_die_anlage_meldet_selbst(graph):
    haende = Counter()
    bma = Counter()
    for endpunkt, szenario in eroeffnungen(
        graph, Erzeugung(gewicht_rd=0, gewicht_brand=50, gewicht_th=50), 800
    ):
        hand = szenario.antworten["eroeffnung.hand"].antwort
        haende[hand] += 1
        if endpunkt.protokoll == "fw.brand.brandmeldeanlage":
            bma[hand] += 1
    assert haende[SELBST] and haende["2-hand-der-anrufer-ist-beim-betroffenen"]
    assert bma["automatische-meldung"] > 0


def test_der_code_29a01_ist_erste_hand(graph):
    gesehen = 0
    for endpunkt, szenario in eroeffnungen(graph, Erzeugung(protokoll="rd.29"), 600):
        if endpunkt.code == "29A01":
            gesehen += 1
            assert szenario.antworten["eroeffnung.hand"].antwort == SELBST
    assert gesehen


def test_geburt_zwischen_16_und_45_und_krankheit_allein(graph):
    geburten = 0
    for endpunkt, szenario in eroeffnungen(graph, Erzeugung(protokoll="rd.24"), 300):
        wert = szenario.antworten["rd.alter"].wert
        if SCHWANGER.search(pfadtext(graph, endpunkt)) and wert:
            geburten += 1
            assert 16 <= int(wert.split()[-1]) <= 45
    assert geburten
    schlaganfaelle = list(eroeffnungen(graph, Erzeugung(protokoll="rd.28"), 100))
    assert schlaganfaelle
    for _, szenario in schlaganfaelle:
        if "rd.anzahl" in szenario.antworten:
            assert szenario.antworten["rd.anzahl"].antwort == "eine-person"


def test_geschaetztes_alter_bleibt_im_rahmen():
    assert geschaetztes_alter(0, 0, 12) == 1
    assert geschaetztes_alter(7, 0, 12) == 8
    assert geschaetztes_alter(63, 18, 90) == 60
    assert geschaetztes_alter(33, 0, 34) == 30
    assert geschaetztes_alter(88, 18, 90) == 90


def test_beziehung_passt_zu_hand_und_alter(graph):
    erzeugung = Erzeugung(gewicht_brand=0, gewicht_th=0, anteil_ohne_adresse=0)
    gesetzt = 0
    for _, szenario in eroeffnungen(graph, erzeugung, 800):
        hand = szenario.antworten["eroeffnung.hand"].antwort
        beziehung = szenario.anrufer.beziehung
        if hand in (SELBST, "automatische-meldung"):
            assert beziehung == ""
            continue
        assert beziehung
        gesetzt += 1
        alter = alter_aus(szenario.antworten["rd.alter"].wert or "") or 0
        if beziehung in ("Ehemann", "Ehefrau"):
            assert alter >= 20 or not szenario.antworten["rd.alter"].wert
        if beziehung in ("Sohn", "Tochter"):
            assert alter >= 38 or not szenario.antworten["rd.alter"].wert
        if szenario.ort.geschoss:
            assert beziehung not in ("Passant", "Passantin")
    assert gesetzt > 300


def passende_quellen():
    zufall = random.Random(3)

    def ort(_, ortsteil="", arten=()):
        art = zufall.choice(sorted(arten)) if arten else "Park"
        return {**PLATZ, "name": "Ort", "art": art}

    return Quellen(adresse=lambda *_: dict(ADRESSE), ort=ort, naechste=lambda *_: dict(ADRESSE))


def platzart(szenario):
    objekt = szenario.ort.objekt
    return objekt[objekt.index("(") + 1 : -1] if objekt.endswith(")") else ""


def mit_quellen(graph, anzahl, **einstellungen):
    endpunkte = {e.knoten: e for e in graph.endpunkte}
    erzeugung = Erzeugung(anteil_ohne_adresse=0, **einstellungen)
    for szenario in viele(graph, anzahl, erzeugung, quellen=passende_quellen()):
        yield endpunkte[szenario.ziel.knoten], szenario


def test_schauplaetze_folgen_der_lage(graph):
    for _, vu in mit_quellen(graph, 60, protokoll="rd.29"):
        assert not vu.ort.geschoss and vu.ort.objekt in STRASSENSTELLEN
    for _, bma in mit_quellen(graph, 60, protokoll="fw.brand.brandmeldeanlage"):
        assert platzart(bma) in OEFFENTLICH_FUER["fw.brand.brandmeldeanlage"]
        assert not bma.ort.geschoss
    wanne = 0
    for _, wasser in mit_quellen(graph, 300, protokoll="rd.14"):
        if wasser.ort.geschoss:
            wanne += 1
            assert alter_aus(wasser.antworten["rd.alter"].wert or "") <= 5
        else:
            assert platzart(wasser) in AM_WASSER | {"Schwimmbad"}
    assert wanne < 300 * 0.15


HAUSNOTIZEN = ("durch die Wand", "Hausnotruf", "Mieter", "aus der Wohnung", "Treppenhaus")


def test_beziehungen_passen_zum_schauplatz(graph):
    gesetzt = 0
    for endpunkt, szenario in mit_quellen(
        graph, 1500, gewicht_rd=50, gewicht_brand=25, gewicht_th=25
    ):
        beziehung = szenario.anrufer.beziehung
        notizen = szenario.rolle.notizen
        zuhause = szenario.ort.objekt == ""
        art = platzart(szenario)
        rd = endpunkt.fachrichtung == "rd"
        gesetzt += bool(beziehung)
        if any(notiz in notizen for notiz in HAUSNOTIZEN):
            assert zuhause, (beziehung, notizen, szenario.ort.objekt)
        if "Aufschaltung" in notizen:
            assert endpunkt.protokoll == "fw.brand.brandmeldeanlage"
        if not rd:
            assert "jemanden liegen" not in notizen
        if rd and beziehung.startswith("Pfleger"):
            alter = alter_aus(szenario.antworten["rd.alter"].wert or "")
            einrichtung = szenario.ort.objekt in EINRICHTUNGEN or art in ("Pflegeheim", "Klinik")
            assert einrichtung or (zuhause and (alter is None or alter >= 65))
        hand = szenario.antworten["eroeffnung.hand"].antwort
        if rd and hand == BEIM_BETROFFENEN and beziehung.startswith("Passant"):
            assert not zuhause
        if art in ("Park", "Spielplatz", "Sportplatz", "Friedhof", "Schwimmbad"):
            assert not beziehung.startswith(("Kunde", "Kundin", "Kolleg"))
        if beziehung.startswith("Trainer"):
            assert RAHMEN_JE_ART.get(art) == "sport"
        if beziehung.startswith(("Rettungsschwimmer", "Angler")):
            assert RAHMEN_JE_ART.get(art) == (
                "bad" if beziehung.startswith("Rett") else "gewaesser"
            )
    assert gesetzt > 800


def test_hergaenge_kennen_den_schauplatz(graph):
    gesehen = Counter()
    for _, szenario in mit_quellen(graph, 2500, protokoll="rd.09"):
        notizen = szenario.rolle.notizen
        art = platzart(szenario)
        if "aus dem Wasser" in notizen:
            gesehen["wasser"] += 1
            assert art in AM_WASSER | {"Schwimmbad"}
        if "Stromschlag" in notizen:
            gesehen["strom"] += 1
            assert szenario.ort.objekt in BETRIEBE
        if "beim Sport" in notizen:
            gesehen["sport"] += 1
            assert RAHMEN_JE_ART[art] in ("draussen", "sport")
        if "im Bett" in notizen:
            assert szenario.ort.objekt == ""
    assert set(gesehen) == {"wasser", "strom", "sport"}


def test_die_funkzelle_liegt_um_den_anrufer(graph):
    breiten = iter(52.40 + 0.03 * i for i in range(100000))

    def adresse(*_):
        return {**ADRESSE, "breite": next(breiten), "laenge": 13.4}

    quellen = Quellen(adresse=adresse, ort=lambda *_: None)
    gesehen = Counter()
    for i in range(600):
        szenario = generieren(graph, quellen, Erzeugung(anteil_orte=0), random.Random(i))
        zelle = szenario.anrufer.funkzelle
        wo = szenario.antworten["eroeffnung.vor-ort"].antwort
        if wo == "unbekannt":
            assert zelle is None
        if zelle is None:
            continue
        abstand = entfernung(zelle.mitte, szenario.ort.koordinaten)
        gesehen[wo] += 1
        if wo == VOR_ORT_JA:
            assert abstand <= zelle.radius
        else:
            assert abstand > zelle.radius
    assert gesehen[VOR_ORT_JA] and gesehen["nein-war-nicht-vor-ort"]


def test_saeuglinge_und_neugeborene_haben_ein_alter_in_monaten_oder_tagen(graph):
    gesehen = set()
    for szenario in viele(graph, 600, Erzeugung(protokoll="rd.09", anteil_ohne_adresse=0)):
        wert = (szenario.antworten.get("rd.alter") or Wahl()).wert or ""
        if szenario.ziel.knoten == NEUGEBORENES:
            assert wert.endswith(" Tage") and 1 <= int(wert.split()[0]) <= 20
            gesehen.add("tage")
        elif wert.endswith(" Monate"):
            assert 1 <= int(wert.split()[0]) <= 11
            assert alter_aus(wert) == 0
            gesehen.add("monate")
        assert wert != "0"
    assert gesehen == {"tage", "monate"}


def gezogene_belastungen(graph, erzeugung):
    belastet = belastungen(graph)
    return {
        name
        for protokolle in ziehbare(graph, erzeugung).values()
        for endpunkte in protokolle.values()
        for endpunkt in endpunkte
        for name in belastet[id(endpunkt)]
    }


def test_belastende_lagen_sind_ohne_freigabe_ausgeschlossen(graph):
    assert gezogene_belastungen(graph, Erzeugung()) == set()
    alle = set(BELASTENDE)
    assert gezogene_belastungen(graph, Erzeugung(belastende=sorted(alle))) == alle


@pytest.mark.parametrize("kategorie", sorted(BELASTENDE))
def test_eine_freigegebene_kategorie_laesst_nur_diese_zu(graph, kategorie):
    gezogen = gezogene_belastungen(graph, Erzeugung(belastende=[kategorie]))
    assert kategorie in gezogen
    belastet = belastungen(graph)
    for protokolle in ziehbare(graph, Erzeugung(belastende=[kategorie])).values():
        for endpunkte in protokolle.values():
            for endpunkt in endpunkte:
                assert belastet[id(endpunkt)] <= {kategorie}


def test_die_kategorien_treffen_was_sie_sollen(graph):
    belastet = belastungen(graph)
    nach_code = {e.code: belastet[id(e)] for e in graph.endpunkte}
    assert "todeszeichen" in nach_code["09B01b"]
    assert nach_code["09B01a"] == frozenset()
    assert any("sexualdelikt" in k for c, k in nach_code.items() if c.startswith("04"))
    assert any("suizid" in k for c, k in nach_code.items() if c.startswith("25"))
    assert all("gewalt" in nach_code[c] for c in nach_code if c.startswith("27"))
    for code in ("25B04", "25D06", "25C00T"):
        assert "suizid" in nach_code[code], code
    assert "gewalt" in nach_code["04A01T"]
    assert any("todeszeichen" in belastet[id(e)] for e in graph.endpunkte if e.protokoll == "rd.14")
    assert not any(belastet[id(e)] for e in graph.endpunkte if e.protokoll in ("rd.02", "rd.03"))


def test_gleichwertige_antworten_meiden_ausgeschlossene_belastungen(graph):
    for knoten_id, knoten in graph.knoten.items():
        antworten = knoten.antworten or []
        if len(antworten) < 2 or len({a.ziel for a in antworten}) != 1:
            continue
        muster = [re.compile(re.escape(antworten[0].label.lower()))]
        person = Person(40, False, False)
        for saat in range(30):
            gezogen = gleichwertige(
                graph, knoten_id, antworten[1].id, person, random.Random(saat), muster
            )
            assert gezogen.id != antworten[0].id
        return
    pytest.skip("kein Knoten mit gleichwertigen Antworten")


def test_eine_einzige_belastende_lage_meldet_nichts_zu_ziehen(graph):
    with pytest.raises(NichtsZuZiehen):
        generieren(graph, QUELLEN, Erzeugung(protokoll="rd.39"), random.Random(1))
    szenario = generieren(
        graph, QUELLEN, Erzeugung(protokoll="rd.39", belastende=["gewalt"]), random.Random(1)
    )
    assert szenario.ziel.code.startswith("39")
