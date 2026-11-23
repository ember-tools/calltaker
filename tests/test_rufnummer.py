import pytest

from rufnummer import normalisieren


@pytest.mark.parametrize(
    ("eingabe", "ziffern"),
    [
        ("0176 1234567", "491761234567"),
        ("+49 176 1234567", "491761234567"),
        ("0049-176-1234567", "491761234567"),
        ("491761234567", "491761234567"),
        ("030 / 685 322 07", "493068532207"),
        ("+49 (0)30 68532207", "493068532207"),
        ("+49 030 68532207", "493068532207"),
        ("", ""),
    ],
)
def test_normalisieren(eingabe, ziffern):
    assert normalisieren(eingabe) == ziffern
