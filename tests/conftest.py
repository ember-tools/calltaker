import pytest

from abfrage import laden
from einstellungen import einstellungen


@pytest.fixture(scope="session")
def graph():
    return laden(einstellungen().abfrage_verzeichnis)


@pytest.fixture
def szenario_daten(graph):
    endpunkt = next(e for e in graph.endpunkte if e.protokoll == "rd.17")
    antworten = {
        schritt.knoten: {
            "antwort": schritt.antwort,
            "label": graph.antwort(schritt.knoten, schritt.antwort).label,
        }
        for schritt in endpunkt.pfad
    }
    antworten["rd.alter"] = {"wert": "81"}
    return {
        "abfrageVersion": graph.meta.version,
        "titel": "Sturz im Treppenhaus, Neukölln",
        "ort": {
            "adresse": {"strasse": "Karl-Marx-Straße", "hausnummer": "92", "plz": "12043"},
            "koordinaten": [52.4793, 13.4385],
            "geschoss": "3. OG",
            "klingel": "Yılmaz",
        },
        "anrufer": {"name": "Ayşe Yılmaz", "rufnummer": "030 68532207"},
        "antworten": antworten,
        "ziel": {"knoten": endpunkt.knoten, "code": endpunkt.code},
        "rolle": {"stimmung": "aufgeregt"},
    }
