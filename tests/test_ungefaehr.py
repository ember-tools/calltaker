import pytest

from ungefaehr import abstand, aehnliche, namen, normal, phonetik

STRASSEN = namen(
    ["Siegmarstraße", "Siegener Straße", "Meyerstraße", "Hermannstraße", "Karl-Marx-Straße"]
)


def test_normalform():
    assert normal("Siegmar-Str.") == normal("siegmarstrasse") == "siegmarstrasse"


@pytest.mark.parametrize(("a", "b"), [("Meyer", "Maier"), ("Mayr", "Meier"), ("Phillip", "Filip")])
def test_gleich_klingendes_hat_denselben_code(a, b):
    assert phonetik(a) == phonetik(b)


def test_abstand_zaehlt_vertauschte_nachbarn_einmal():
    assert abstand("kral", "karl", 2) == 1
    assert abstand("hermanstrasse", "hermannstrasse", 2) == 1
    assert abstand("abcdef", "uvwxyz", 2) == 3


def test_tippfehler_und_klang_finden_strassen_naechste_zuerst():
    assert aehnliche(STRASSEN, "siegmartstrase")[0] == "Siegmarstraße"
    assert aehnliche(STRASSEN, "Hermanstr") == ["Hermannstraße"]
    assert aehnliche(STRASSEN, "Kral-Marx")[0] == "Karl-Marx-Straße"
    assert "Meyerstraße" in aehnliche(STRASSEN, "Maierstr")
    assert aehnliche(namen(["Oranienstraße"]), "Hermanstr") == []


def test_exakte_anfaenge_und_kurze_texte_bleiben_aussen_vor():
    assert "Siegmarstraße" not in aehnliche(STRASSEN, "Siegmar")
    assert aehnliche(STRASSEN, "Sie") == []
