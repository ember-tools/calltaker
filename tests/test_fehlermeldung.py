import pytest
from pydantic import ValidationError

from fehlermeldung import deutsch
from szenario import Rolle


def test_auswahlen_werden_mit_oder_aufgezaehlt():
    with pytest.raises(ValidationError) as fehler:
        Rolle.model_validate({"stimmung": "froh"})
    assert deutsch(fehler.value.errors()) == (
        "stimmung: muss 'ruhig', 'aufgeregt', 'panisch' oder 'verwirrt' sein"
    )
