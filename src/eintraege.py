"""What the trainee enters during a call: location, caller, the path through the questions, notes.

The trainee's view holds these entries and sends them whole whenever they change; the server
keeps them on the call, so the trainer sees them and the debrief compares them with the truth.
The server stamps, from its own clock, when the location and the code were first entered, when
CPR guidance first started and when each instruction to the caller was first ticked.
Whether the questioning has reached a code is decided by the view, with the same rules that
decide whether the call is complete, and sent as `codeErreicht`; the server only times it.
"""

from typing import Annotated

from pydantic import Field

from szenario import Adresse, Modell

TEXT = 500
LANGER_TEXT = 4000
ANLEITUNGEN_HOECHSTENS = 100
PFAD_HOECHSTENS = 200


class Warntafel(Modell):
    """An orange plate as entered: hazard number on top, UN number below."""

    un: str = Field("", max_length=8)
    gefahrenzahl: str = Field("", max_length=8)


class Ortseintrag(Modell):
    """The location as entered."""

    adresse: Adresse = Field(default_factory=Adresse)
    koordinaten: tuple[float, float] | None = None
    objekt: str = Field("", max_length=TEXT)
    geschoss: str = Field("", max_length=TEXT)
    klingel: str = Field("", max_length=TEXT)
    anfahrt: str = Field("", max_length=TEXT)
    gefahren: str = Field("", max_length=TEXT)
    gefahrgut: Warntafel = Field(default_factory=Warntafel)


class Anrufereintrag(Modell):
    """The caller as entered: the name, and whether the shown number was confirmed."""

    name: str = Field("", max_length=TEXT)
    rufnummer_bestaetigt: bool = False
    rueckrufnummer: str = Field("", max_length=40)


class Schritteintrag(Modell):
    """One step of the trainee's path: the node, and the answer chosen or the value typed.

    `automatisch` marks a step the questioning took itself because earlier answers decided it.
    """

    knoten: str = Field(max_length=200)
    antwort: str | None = Field(None, max_length=200)
    wert: str | None = Field(None, max_length=TEXT)
    automatisch: bool = False


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
    """When the location, the code and each instruction were first entered, by server time."""

    adresse: float | None = None
    code: float | None = None
    anleitungen: dict[str, float] = Field(default_factory=dict)
    reanimation: float | None = None


class Reanimationseintrag(Modell):
    """The CPR guidance: whether its beat runs, and at how many beats a minute."""

    laeuft: bool = False
    takt: int = Field(100, ge=100, le=120)


class Anleitungseintrag(Modell):
    """The instructions to the caller the trainee ticked as given, by id."""

    gegeben: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list, max_length=ANLEITUNGEN_HOECHSTENS
    )


class Eintraege(Modell):
    """Everything the trainee entered during one call."""

    ort: Ortseintrag = Field(default_factory=Ortseintrag)
    anrufer: Anrufereintrag = Field(default_factory=Anrufereintrag)
    betroffener: str = Field("", max_length=TEXT)
    abfrage: Abfrageeintrag = Field(default_factory=Abfrageeintrag)
    hinweise: str = Field("", max_length=LANGER_TEXT)
    anleitung: Anleitungseintrag = Field(default_factory=Anleitungseintrag)
    reanimation: Reanimationseintrag = Field(default_factory=Reanimationseintrag)
    zeiten: Zeiten = Field(default_factory=Zeiten)

    def nach_aussen(self) -> dict:
        """Return the entries as the views read them."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


def uebernehmen(bisher: Eintraege, neu: Eintraege, jetzt: float) -> Eintraege:
    """Take new entries from the trainee, keeping the server's times and stamping new ones.

    The location counts as entered once it has a point; the code once the view reports it; CPR
    once its beat first runs; an instruction once it is ticked, and its time stays even if the
    tick is taken back. At most `ANLEITUNGEN_HOECHSTENS` instructions are timed, so a client
    cannot grow the times without end.
    """
    zeiten = bisher.zeiten.model_copy(deep=True)
    if zeiten.reanimation is None and neu.reanimation.laeuft:
        zeiten.reanimation = jetzt
    for id_ in neu.anleitung.gegeben:
        if id_ in zeiten.anleitungen or len(zeiten.anleitungen) < ANLEITUNGEN_HOECHSTENS:
            zeiten.anleitungen.setdefault(id_, jetzt)
    if zeiten.adresse is None and neu.ort.koordinaten is not None:
        zeiten.adresse = jetzt
    if zeiten.code is None and neu.abfrage.code_erreicht:
        zeiten.code = jetzt
    return neu.model_copy(update={"zeiten": zeiten})
