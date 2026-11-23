import re

import pytest

from anruf import Anruf, Anrufzustand
from rolle import Rolle
from szenario import Szenario
from uebung import ONLINE_FRIST, UNBESUCHT_FRIST, Uebungen, UebungenVoll


class Uhr:
    """A clock the test moves by hand."""

    def __init__(self) -> None:
        """Start at a fixed time."""
        self.jetzt = 1000.0

    def __call__(self) -> float:
        """Return the current time."""
        return self.jetzt


@pytest.fixture
def uhr():
    return Uhr()


def test_codes_sind_lesbar_und_finden_die_rolle(uhr):
    alle = Uebungen(uhr)
    uebung = alle.anlegen()
    assert re.fullmatch(r"A-[A-HJ-NP-Z2-9]{8}", uebung.ausbilder_code)
    assert re.fullmatch(r"T-[A-HJ-NP-Z2-9]{8}", uebung.trainee_code)
    assert alle.finden(uebung.ausbilder_code.lower()) == (uebung, Rolle.AUSBILDER)
    assert alle.finden(f" {uebung.trainee_code} ") == (uebung, Rolle.TRAINEE)
    assert alle.finden("A-XXXXXX") is None


def test_die_zahl_der_uebungen_ist_begrenzt(uhr):
    alle = Uebungen(uhr, hoechstens=2)
    alle.anlegen()
    alle.anlegen()
    with pytest.raises(UebungenVoll):
        alle.anlegen()


def test_aufraeumen_entfernt_nur_verlassene_uebungen(uhr):
    alle = Uebungen(uhr, frist=3600)
    alt = alle.anlegen()
    aktiv = alle.anlegen()
    alt.abgefragt(Rolle.AUSBILDER)
    uhr.jetzt += 3000
    aktiv.abgefragt(Rolle.TRAINEE)
    uhr.jetzt += 700
    assert alle.aufraeumen() == [alt]
    assert alle.finden(alt.ausbilder_code) is None
    assert alle.finden(aktiv.trainee_code) is not None


def test_nie_geoeffnete_uebungen_leben_nur_kurz(uhr):
    alle = Uebungen(uhr, frist=3600)
    nie = alle.anlegen()
    uhr.jetzt += UNBESUCHT_FRIST + 1
    assert alle.aufraeumen() == [nie]


def test_eine_volle_verwaltung_raeumt_vor_dem_ablehnen_auf(uhr):
    alle = Uebungen(uhr, hoechstens=1, frist=3600)
    alle.anlegen()
    uhr.jetzt += UNBESUCHT_FRIST + 1
    assert alle.anlegen() is not None


def test_verbunden_ist_wer_kuerzlich_abgefragt_hat(uhr):
    uebung = Uebungen(uhr).anlegen()
    start = uebung.version
    uebung.abgefragt(Rolle.TRAINEE)
    assert uebung.verbunden[Rolle.TRAINEE]
    assert uebung.version == start + 1
    uhr.jetzt += ONLINE_FRIST
    uebung.verbindungen_pruefen()
    assert uebung.verbunden[Rolle.TRAINEE]
    uhr.jetzt += 0.1
    uebung.verbindungen_pruefen()
    assert not uebung.verbunden[Rolle.TRAINEE]
    assert uebung.version == start + 2


@pytest.fixture
def anruf(szenario_daten, uhr):
    return Anruf(szenario=Szenario.model_validate(szenario_daten), klingelt_seit=uhr())


def test_der_trainee_sieht_die_wahrheit_erst_nach_dem_ende(anruf):
    wartend = anruf.fuer_trainee()
    assert wartend["rufnummer"] == "493068532207"
    assert "szenario" not in wartend
    assert "eintraege" not in wartend
    anruf.zustand = Anrufzustand.GESPRAECH
    anruf.angenommen_um = 1001.0
    assert "szenario" not in anruf.fuer_trainee()
    assert anruf.fuer_trainee()["eintraege"] == {}
    anruf.zustand = Anrufzustand.BEENDET
    assert anruf.fuer_trainee()["szenario"]["titel"] == "Sturz im Treppenhaus, Neukölln"


def test_ein_aufgelegter_anruf_zeigt_nur_nummer_und_wartezeit(anruf):
    anruf.zustand = Anrufzustand.AUFGELEGT
    anruf.beendet_um = 1100.0
    assert set(anruf.fuer_trainee()) == {
        "id",
        "zustand",
        "klingeltSeit",
        "rufnummer",
        "rufnummerUnterdrueckt",
        "beendetUm",
    }


def test_eine_unterdrueckte_nummer_bleibt_verborgen(szenario_daten, uhr):
    anrufer = {"name": "X", "rufnummerUnterdrueckt": True, "rueckrufnummer": "0176 1234567"}
    szenario = Szenario.model_validate({**szenario_daten, "anrufer": anrufer})
    sicht = Anruf(szenario=szenario, klingelt_seit=uhr()).fuer_trainee()
    assert "rufnummer" not in sicht
    assert sicht["rufnummerUnterdrueckt"] is True
    assert "491761234567" not in str(sicht)


def test_der_zustand_ist_nach_rolle_gefiltert(anruf, uhr):
    uebung = Uebungen(uhr).anlegen()
    uebung.anrufe.append(anruf)
    uebung.spiegel = {"strasse": "Karl"}
    trainee = uebung.zustand(Rolle.TRAINEE)
    ausbilder = uebung.zustand(Rolle.AUSBILDER)
    assert set(trainee) == {"verbunden", "engine", "anrufe"}
    assert "parameter" not in trainee["engine"]
    assert ausbilder["engine"]["parameter"]["maxSchlange"] == 5
    assert "szenario" not in trainee["anrufe"][0]
    assert ausbilder["codes"]["trainee"] == uebung.trainee_code
    assert ausbilder["anrufe"][0]["szenario"]["titel"]
    assert ausbilder["spiegel"] == {"strasse": "Karl"}
