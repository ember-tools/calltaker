import random
import statistics

import pytest
from pydantic import ValidationError

from anruf import Anrufzustand
from engine import AUTOMATISCHE_PAUSE_NACH, Parameter
from rolle import Rolle
from szenario import Szenario
from uebung import Uebungen


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


@pytest.fixture
def uebung(uhr, szenario_daten):
    uebung = Uebungen(uhr).anlegen()
    uebung.engine.zufall = random.Random(7)
    for nummer in range(30):
        uebung.pool.hinzufuegen(Szenario.model_validate({**szenario_daten, "titel": f"S{nummer}"}))
    return uebung


def anwesend(uebung, uhr):
    for rolle in Rolle:
        uebung.letzte_abfrage[rolle] = uhr.jetzt


def laufen(uebung, uhr, sekunden, anwesend_bleiben=True):
    for _ in range(int(sekunden)):
        uhr.jetzt += 1
        if anwesend_bleiben:
            anwesend(uebung, uhr)
        uebung.engine.takt()


def wartend(uebung):
    return uebung.engine.wartende()


def test_vor_dem_start_klingelt_nichts(uebung, uhr):
    laufen(uebung, uhr, 120)
    assert uebung.anrufe == []


def test_der_erste_anruf_klingelt_nach_fuenf_bis_zehn_sekunden(uebung, uhr):
    anwesend(uebung, uhr)
    uebung.engine.starten()
    laufen(uebung, uhr, 4)
    assert uebung.anrufe == []
    laufen(uebung, uhr, 6)
    assert len(wartend(uebung)) == 1
    assert wartend(uebung)[0].szenario.titel == "S0"
    assert len(uebung.pool.szenarien) == 29


def test_ohne_szenarien_klingelt_nichts(uhr):
    uebung = Uebungen(uhr).anlegen()
    anwesend(uebung, uhr)
    uebung.engine.starten()
    laufen(uebung, uhr, 60)
    assert uebung.anrufe == []


def test_angenommen_wird_nur_der_am_laengsten_wartende(uebung, uhr):
    anwesend(uebung, uhr)
    uebung.engine.starten()
    uebung.engine.sofort_klingeln(uebung.pool.szenarien[0].id)
    uebung.engine.sofort_klingeln(uebung.pool.szenarien[0].id)
    erster, zweiter = wartend(uebung)
    with pytest.raises(ValueError, match="am längsten wartende"):
        uebung.engine.annehmen(zweiter.id)
    uebung.engine.annehmen(erster.id)
    assert erster.zustand == Anrufzustand.GESPRAECH
    assert erster.angenommen_um == uhr.jetzt
    with pytest.raises(ValueError, match="schon ein Gespräch"):
        uebung.engine.annehmen(zweiter.id)
    uebung.engine.beenden()
    assert erster.zustand == Anrufzustand.BEENDET
    with pytest.raises(ValueError, match="kein Gespräch"):
        uebung.engine.beenden()


@pytest.mark.parametrize("wartende", [0, 1, 2, 3])
def test_der_abstand_im_gespraech_waechst_mit_der_schlange(uebung, uhr, wartende):
    anwesend(uebung, uhr)
    uebung.engine.starten()
    for _ in range(wartende + 1):
        uebung.engine.sofort_klingeln(uebung.pool.szenarien[0].id)
    uebung.engine.annehmen(wartend(uebung)[0].id)
    abstaende = []
    for _ in range(4000):
        uebung.engine._neu_planen()
        abstaende.append(uebung.engine.naechstes_klingeln - uhr.jetzt)
    erwartet = 45 * 1.6**wartende
    assert statistics.mean(abstaende) == pytest.approx(erwartet, rel=0.06)


def test_die_geduld_liegt_meist_zwischen_den_grenzen(uebung):
    zuege = sorted(uebung.engine._geduld() for _ in range(20000))
    assert zuege[1000] == pytest.approx(60, rel=0.06)
    assert zuege[19000] == pytest.approx(300, rel=0.06)


def test_die_schlange_waechst_nie_ueber_die_grenze(uebung, uhr):
    uebung.engine.parameter_setzen(
        Parameter(geduld_min=5000, geduld_max=6000, basis_abstand=5, abstand_faktor=1)
    )
    anwesend(uebung, uhr)
    uebung.engine.starten()
    laufen(uebung, uhr, 15)
    uebung.engine.annehmen(wartend(uebung)[0].id)
    laufen(uebung, uhr, 600)
    assert len(wartend(uebung)) == 5
    with pytest.raises(ValueError, match="voll"):
        uebung.engine.sofort_klingeln(uebung.pool.szenarien[0].id)


def test_ungeduldige_anrufer_legen_auf_und_kommen_in_den_pool(uebung, uhr):
    uebung.engine.parameter_setzen(Parameter(geduld_min=20, geduld_max=20.0001))
    anwesend(uebung, uhr)
    uebung.engine.starten()
    anruf = uebung.engine.sofort_klingeln(uebung.pool.szenarien[0].id)
    laufen(uebung, uhr, 19)
    assert anruf.zustand == Anrufzustand.WARTET
    laufen(uebung, uhr, 2)
    assert anruf.zustand == Anrufzustand.AUFGELEGT
    assert anruf.beendet_um is not None
    assert uebung.pool.szenarien[-1].titel == anruf.szenario.titel


def test_ohne_rueckgabe_bleibt_der_pool_kleiner(uebung, uhr):
    uebung.engine.parameter_setzen(Parameter(zurueck_in_pool=False))
    anwesend(uebung, uhr)
    uebung.engine.starten()
    anruf = uebung.engine.sofort_klingeln(uebung.pool.szenarien[0].id)
    uebung.engine.auflegen(anruf.id)
    assert anruf.zustand == Anrufzustand.AUFGELEGT
    assert len(uebung.pool.szenarien) == 29


def test_eine_pause_haelt_die_wartezeiten_an(uebung, uhr):
    uebung.engine.parameter_setzen(Parameter(geduld_min=60, geduld_max=60.0001))
    anwesend(uebung, uhr)
    uebung.engine.starten()
    anruf = uebung.engine.sofort_klingeln(uebung.pool.szenarien[0].id)
    seit = anruf.klingelt_seit
    laufen(uebung, uhr, 30)
    uebung.engine.pausieren(True)
    anzahl = len(uebung.anrufe)
    laufen(uebung, uhr, 600)
    assert len(uebung.anrufe) == anzahl
    assert anruf.zustand == Anrufzustand.WARTET
    uebung.engine.pausieren(False)
    assert anruf.klingelt_seit == seit + 600
    laufen(uebung, uhr, 25)
    assert anruf.zustand == Anrufzustand.WARTET
    laufen(uebung, uhr, 10)
    assert anruf.zustand == Anrufzustand.AUFGELEGT


def test_fehlt_eine_seite_pausiert_die_engine_von_selbst(uebung, uhr):
    anwesend(uebung, uhr)
    uebung.engine.starten()
    laufen(uebung, uhr, int(AUTOMATISCHE_PAUSE_NACH) + 1, anwesend_bleiben=False)
    assert uebung.engine.automatisch_pausiert
    assert uebung.engine.pausiert
    laufen(uebung, uhr, 1)
    assert not uebung.engine.automatisch_pausiert


def test_eine_manuelle_pause_ueberdauert_die_rueckkehr(uebung, uhr):
    anwesend(uebung, uhr)
    uebung.engine.starten()
    uebung.engine.pausieren(True)
    laufen(uebung, uhr, 20, anwesend_bleiben=False)
    laufen(uebung, uhr, 1)
    assert uebung.engine.pausiert
    assert uebung.engine.manuell_pausiert


def test_parameter_brauchen_stimmige_spannen():
    with pytest.raises(ValidationError, match="Geduld"):
        Parameter(geduld_min=300, geduld_max=60)
    with pytest.raises(ValidationError):
        Parameter(max_schlange=0)


def test_im_gleichgewicht_pendelt_die_schlange(uebung, uhr, szenario_daten):
    """Run ten simulated hours with a trainee stuck on one call and measure the queue."""
    uebung.engine.zufall = random.Random(42)
    for nummer in range(170):
        uebung.pool.hinzufuegen(Szenario.model_validate({**szenario_daten, "titel": f"T{nummer}"}))
    anwesend(uebung, uhr)
    uebung.engine.starten()
    laufen(uebung, uhr, 15)
    uebung.engine.annehmen(wartend(uebung)[0].id)
    laengen = []
    for _ in range(10 * 3600):
        uhr.jetzt += 1
        anwesend(uebung, uhr)
        uebung.engine.takt()
        laengen.append(len(wartend(uebung)))
    mittel = statistics.mean(laengen)
    anteil_voll = laengen.count(5) / len(laengen)
    assert 1.4 <= mittel <= 1.9
    assert anteil_voll < 0.01
    assert max(laengen) <= 5


def test_auflegen_in_einen_vollen_pool_verwirft_das_szenario(
    uebung, uhr, szenario_daten, monkeypatch
):
    import pool as pool_modul

    monkeypatch.setattr(pool_modul, "POOL_HOECHSTENS", 30)
    anwesend(uebung, uhr)
    uebung.engine.starten()
    anruf = uebung.engine.sofort_klingeln(uebung.pool.szenarien[0].id)
    uebung.pool.hinzufuegen(Szenario.model_validate(szenario_daten))
    vorher = uebung.version
    uebung.engine.auflegen(anruf.id)
    assert anruf.zustand == Anrufzustand.AUFGELEGT
    assert len(uebung.pool.szenarien) == 30
    assert uebung.version > vorher


def test_bereit_waehrend_der_ausbilder_fehlt_klingelt_nach_seiner_ankunft_bald(uebung, uhr):
    laufen(uebung, uhr, 300, anwesend_bleiben=False)
    uebung.letzte_abfrage[Rolle.TRAINEE] = uhr.jetzt
    uebung.engine.starten()
    assert uebung.engine.pausiert
    laufen(uebung, uhr, 10)
    assert len(wartend(uebung)) == 1


def test_ein_anruf_waehrend_der_pause_wartet_erst_ab_ihrem_ende(uebung, uhr):
    anwesend(uebung, uhr)
    uebung.engine.starten()
    uebung.engine.pausieren(True)
    laufen(uebung, uhr, 100)
    anruf = uebung.engine.sofort_klingeln(uebung.pool.szenarien[0].id)
    laufen(uebung, uhr, 100)
    uebung.engine.pausieren(False)
    assert anruf.klingelt_seit == uhr.jetzt


def test_annehmen_waehrend_der_pause_zaehlt_nur_die_laufzeit(uebung, uhr):
    anwesend(uebung, uhr)
    uebung.engine.starten()
    anruf = uebung.engine.sofort_klingeln(uebung.pool.szenarien[0].id)
    laufen(uebung, uhr, 15)
    laufen(uebung, uhr, 200, anwesend_bleiben=False)
    assert uebung.engine.pausiert
    uebung.engine.annehmen(anruf.id)
    assert anruf.angenommen_um - anruf.klingelt_seit == pytest.approx(
        15 + AUTOMATISCHE_PAUSE_NACH + 1
    )


def test_die_ansichten_sehen_seit_wann_pausiert_ist(uebung, uhr):
    anwesend(uebung, uhr)
    uebung.engine.starten()
    uebung.engine.pausieren(True)
    for rolle in Rolle:
        assert uebung.engine.zustand(rolle)["pausiertSeit"] == uhr.jetzt
    uebung.engine.pausieren(False)
    assert "pausiertSeit" not in uebung.engine.zustand(Rolle.TRAINEE)


def test_jeder_wechsel_eines_pausenschalters_erhoeht_die_version(uebung, uhr):
    anwesend(uebung, uhr)
    uebung.engine.starten()
    laufen(uebung, uhr, 12, anwesend_bleiben=False)
    assert uebung.engine.automatisch_pausiert
    vorher = uebung.version
    uebung.engine.pausieren(True)
    assert uebung.version > vorher
    vorher = uebung.version
    laufen(uebung, uhr, 1)
    assert not uebung.engine.automatisch_pausiert
    assert uebung.version > vorher


def test_ein_neu_gezogenes_klingeln_erhoeht_die_version(uhr):
    uebung = Uebungen(uhr).anlegen()
    anwesend(uebung, uhr)
    uebung.engine.starten()
    vorher = uebung.version
    laufen(uebung, uhr, 11)
    assert uebung.anrufe == []
    assert uebung.version > vorher


def test_alte_anrufe_werden_begrenzt(uebung, uhr, monkeypatch):
    import engine as engine_modul

    monkeypatch.setattr(engine_modul, "ANRUFE_HOECHSTENS", 5)
    anwesend(uebung, uhr)
    uebung.engine.starten()
    for _ in range(8):
        uebung.engine.annehmen(uebung.engine.sofort_klingeln(uebung.pool.szenarien[0].id).id)
        uebung.engine.beenden()
    offen = uebung.engine.sofort_klingeln(uebung.pool.szenarien[0].id)
    assert len(uebung.anrufe) == 5
    assert uebung.anrufe[-1] is offen


def test_das_naechste_klingeln_liegt_fuer_den_ausbilder_nie_in_der_vergangenheit(uebung, uhr):
    anwesend(uebung, uhr)
    uebung.engine.starten()
    uebung.engine.pausieren(True)
    laufen(uebung, uhr, 300)
    uebung.engine.sofort_klingeln(uebung.pool.szenarien[0].id)
    assert uebung.engine.zustand(Rolle.AUSBILDER)["naechstesKlingeln"] >= uhr.jetzt


def test_beide_rollen_sehen_die_zielzeiten(uebung):
    engine = uebung.engine
    engine.parameter_setzen(engine.parameter.model_copy(update={"ziel_reanimation": 90}))
    for rolle in Rolle:
        assert engine.zustand(rolle)["ziele"] == {"reanimation": 90, "uebergabe": 60}
