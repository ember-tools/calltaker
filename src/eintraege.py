"""What the trainee enters during a call: location, caller, the path through the questions, notes.

The trainee's view holds these entries and sends them whole whenever they change; the server
keeps them on the call, so the trainer sees them and the debrief compares them with the truth.
The server stamps when the location and when the code were first entered, from its own clock.
Whether the questioning has reached a code is decided by the view, with the same rules that
decide whether the call is complete, and sent as `codeErreicht`; the server only times it.
"""

from pydantic import Field

from szenario import Adresse, Modell

TEXT = 500
LANGER_TEXT = 4000
PFAD_HOECHSTENS = 200


class Ortseintrag(Modell):
    """The location as entered."""

    adresse: Adresse = Field(default_factory=Adresse)
    koordinaten: tuple[float, float] | None = None
    objekt: str = Field("", max_length=TEXT)
    geschoss: str = Field("", max_length=TEXT)
    klingel: str = Field("", max_length=TEXT)
    anfahrt: str = Field("", max_length=TEXT)
    gefahren: str = Field("", max_length=TEXT)


class Anrufereintrag(Modell):
    """The caller as entered: the name, and whether the shown number was confirmed."""

    name: str = Field("", max_length=TEXT)
    rufnummer_bestaetigt: bool = False
    rueckrufnummer: str = Field("", max_length=40)


class Schritteintrag(Modell):
    """One step of the trainee's path: the node, and the answer chosen or the value typed."""

    knoten: str = Field(max_length=200)
    antwort: str | None = Field(None, max_length=200)
    wert: str | None = Field(None, max_length=TEXT)


class Codewahl(Modell):
    """An endpoint chosen outside the path: by upgrading, or as the interim result on cancelling."""

    knoten: str = Field(max_length=200)
    code: str = Field(max_length=40)


class Abbruch(Modell):
    """A cancelled questioning: the reason, and the interim result that stands as the code."""

    grund: str = Field(max_length=TEXT)
    ergebnis: Codewahl | None = None


class Abfrageeintrag(Modell):
    """The questioning as done: the path, and an upgrade or a cancellation, if any."""

    pfad: list[Schritteintrag] = Field(default_factory=list, max_length=PFAD_HOECHSTENS)
    aufwertung: Codewahl | None = None
    abbruch: Abbruch | None = None
    code_erreicht: bool = False


class Zeiten(Modell):
    """When the location and the code were first entered, by the server's clock."""

    adresse: float | None = None
    code: float | None = None


class Eintraege(Modell):
    """Everything the trainee entered during one call."""

    ort: Ortseintrag = Field(default_factory=Ortseintrag)
    anrufer: Anrufereintrag = Field(default_factory=Anrufereintrag)
    betroffener: str = Field("", max_length=TEXT)
    abfrage: Abfrageeintrag = Field(default_factory=Abfrageeintrag)
    hinweise: str = Field("", max_length=LANGER_TEXT)
    zeiten: Zeiten = Field(default_factory=Zeiten)

    def nach_aussen(self) -> dict:
        """Return the entries as the views read them."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


def uebernehmen(bisher: Eintraege, neu: Eintraege, jetzt: float) -> Eintraege:
    """Take new entries from the trainee, keeping the server's times and stamping new ones.

    The location counts as entered once it has a point; the code once the view reports it.
    """
    zeiten = bisher.zeiten.model_copy()
    if zeiten.adresse is None and neu.ort.koordinaten is not None:
        zeiten.adresse = jetzt
    if zeiten.code is None and neu.abfrage.code_erreicht:
        zeiten.code = jetzt
    return neu.model_copy(update={"zeiten": zeiten})
