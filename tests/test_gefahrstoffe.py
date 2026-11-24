import importlib.util
import json
from pathlib import Path

from fastapi.testclient import TestClient

import gefahrstoffe
from main import anwendung_bauen
from szenario import Wahl, wahlbefunde

WERKZEUG = Path(__file__).resolve().parent.parent / "tools" / "un_nummern_uebernehmen.py"
_spec = importlib.util.spec_from_file_location("un_nummern_uebernehmen", WERKZEUG)
un_nummern_uebernehmen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(un_nummern_uebernehmen)

DATEN = Path(__file__).resolve().parent.parent / "daten" / "gefahrstoffe"

SEITE = """
<table class="toc"><tr><td>Inhalt</td></tr></table>
<table cellpadding="0" class="prettytable">
<tr><th>UN</th><th>Zahl</th><th>Klasse</th><th>Name</th></tr>
<tr><td>0005 - 0007 </td><td> &nbsp; </td><td> 1 </td><td> Patronen, mit <a>Sprengladung</a>
</td></tr>
<tr><td>1428 </td><td> X423 </td><td> 4.3 </td><td> Natrium</td></tr>
<tr><td>1203 </td><td> 33 </td><td> 3 </td><td> Benzin</td></tr>
</table>
"""


def test_das_werkzeug_liest_zeilen_und_loest_bereiche_auf():
    eintraege = un_nummern_uebernehmen.eintraege(SEITE)
    assert [e["un"] for e in eintraege] == ["0005", "0006", "0007", "1203", "1428"]
    assert eintraege[0] == {
        "un": "0005",
        "gefahrenzahl": "",
        "klasse": "1",
        "bezeichnung": "Patronen, mit Sprengladung",
    }
    assert eintraege[-1]["gefahrenzahl"] == "X423"


def test_die_mitgelieferte_liste_laedt_mit_herkunft():
    stoffe = gefahrstoffe.laden(DATEN)
    assert len(stoffe) > 2000
    assert any(s.un == "1203" and s.gefahrenzahl == "33" for s in stoffe)
    assert all(s.gefahrenzahl for s in gefahrstoffe.mit_warntafel(stoffe))
    assert "GNU" in gefahrstoffe.herkunft(DATEN)["lizenz"]


def test_ohne_liste_gibt_es_keine_stoffe(tmp_path):
    assert gefahrstoffe.laden(tmp_path) == []
    assert gefahrstoffe.herkunft(tmp_path) == {}


def test_die_liste_ist_ueber_die_api_abrufbar():
    with TestClient(anwendung_bauen()) as client:
        antwort = client.get("/api/gefahrstoffe")
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["herkunft"]["quelle"].startswith("https://www.chemie.de/")
    assert json.dumps(daten["stoffe"][0], ensure_ascii=False).startswith('{"un": "0004"')


def test_gezogen_werden_nur_tafeln_mit_einer_gefahrenzahl():
    stoffe = gefahrstoffe.mit_warntafel(gefahrstoffe.laden(DATEN))
    assert len(stoffe) > 1500
    assert all(gefahrstoffe.GEFAHRENZAHL.match(stoff.gefahrenzahl) for stoff in stoffe)
    zusammen = gefahrstoffe.Stoff(un="1993", gefahrenzahl="30 + 33", klasse="3", bezeichnung="x")
    verboten = gefahrstoffe.Stoff(un="0020", gefahrenzahl="?", klasse="1", bezeichnung="y")
    assert gefahrstoffe.mit_warntafel([zusammen, verboten]) == []


def test_die_tafelfrage_steht_in_den_vier_protokollen_hinter_dem_gefahrgut(graph):
    tafelfragen = {
        kid for kid, k in graph.knoten.items() if k.eingabe and k.eingabe.art == "warntafel"
    }
    assert tafelfragen == {
        "fw.th.gefahrstoffe.warntafel",
        "fw.th.verkehrsunfall.warntafel",
        "fw.brand.fahrzeugbrand.warntafel",
        "fw.brand.industrie-und-gewerbebrand.warntafel",
    }
    assert (
        graph.antwort("fw.th.verkehrsunfall.k3", "gefahrgut").ziel
        == "fw.th.verkehrsunfall.warntafel"
    )
    assert (
        graph.antwort("fw.th.verkehrsunfall.k3", "kein-gefahrgut").ziel
        != "fw.th.verkehrsunfall.warntafel"
    )


def test_eine_tafel_im_szenario_braucht_die_richtige_form(graph):
    knoten = "fw.th.verkehrsunfall.warntafel"
    assert wahlbefunde(graph, knoten, Wahl(wert="33/1203")) == []
    assert wahlbefunde(graph, knoten, Wahl(wert="/0004")) == []
    assert wahlbefunde(graph, knoten, Wahl()) == []
    assert wahlbefunde(graph, knoten, Wahl(wert="Benzin"))[0].art == "fehler"
