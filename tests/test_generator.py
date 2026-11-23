import random

from generator import NAMENSGRUPPEN, festnetznummer, mobilnummer, zufallsname


def nachnamen_der_gruppen(vorname: str) -> set[str]:
    nachnamen = set()
    for gruppe in NAMENSGRUPPEN:
        if vorname not in {name for name, _ in gruppe.vornamen}:
            continue
        for nachname in gruppe.nachnamen:
            nachnamen.update([nachname] if isinstance(nachname, str) else nachname)
    return nachnamen


def test_vor_und_nachname_kommen_aus_einer_gruppe():
    zufall = random.Random(1)
    for _ in range(200):
        vorname, nachname = zufallsname(zufall).split(" ", 1)
        assert nachname in nachnamen_der_gruppen(vorname)


def test_polnische_nachnamen_richten_sich_nach_dem_geschlecht():
    zufall = random.Random(3)
    frauen = {zufallsname(zufall, weiblich=True) for _ in range(2000)}
    maenner = {zufallsname(zufall, weiblich=False) for _ in range(2000)}
    assert not any(name.endswith(("ski", "ński")) for name in frauen)
    assert any(name.endswith("ska") for name in frauen)
    assert not any(name.endswith("ska") for name in maenner)
    assert any(name.endswith("ski") for name in maenner)


def test_nummern_haben_landesvorwahl_und_laenge():
    zufall = random.Random(2)
    assert festnetznummer(zufall).startswith("4930")
    assert len(festnetznummer(zufall)) == 12
    mobil = mobilnummer(zufall)
    assert mobil.startswith("491")
    assert len(mobil) == 12
