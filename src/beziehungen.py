"""Who the caller is to the affected person, so the trainer knows whom to play.

The relationship follows who reports (the hand), where it happens (the scene) and how old the
affected person is: a son calls for his mother, not for a twenty-year-old; a passer-by calls from
the street, not from the living room. Each entry names the relationship for a male and a female
caller, its weight, and the ages of the affected person it fits. Callers who are not there get a
note on how they learned of it, for the role notes.
"""

import random
from dataclasses import dataclass

from meldehand import AUTOMATISCH, BEIM_BETROFFENEN, FUER_ANDERE, GEHOERT, SELBST


@dataclass(frozen=True)
class Beziehung:
    """One relationship: its male and female form, weight, ages it fits, and what it knows."""

    mann: str
    frau: str
    gewicht: float
    von: int = 0
    bis: int = 120
    vertraut: bool = False
    notiz: str = ""

    def form(self, weiblich: bool) -> str:
        """Return the relationship as the caller would name themselves."""
        return self.frau if weiblich else self.mann

    def passt(self, alter: int | None) -> bool:
        """Tell whether the relationship fits the affected person's age, unknown ages fit all."""
        return alter is None or self.von <= alter <= self.bis


def b(mann: str, frau: str, gewicht: float, von: int = 0, bis: int = 120, **mehr) -> Beziehung:
    """Shorthand for a table row."""
    return Beziehung(mann, frau, gewicht, von, bis, **mehr)


ZWEITE_HAND = {
    "wohnung": (
        b("Ehemann", "Ehefrau", 20, 20, vertraut=True),
        b("Partner", "Partnerin", 10, 20, vertraut=True),
        b("Sohn", "Tochter", 20, 38, vertraut=True),
        b("Vater", "Mutter", 15, 0, 30, vertraut=True),
        b("Nachbar", "Nachbarin", 15, vertraut=True),
        b("Mitbewohner", "Mitbewohnerin", 10, 16, 45, vertraut=True),
        b("Pfleger des Pflegedienstes", "Pflegerin des Pflegedienstes", 5, 65, vertraut=True),
        b("Enkel", "Enkelin", 5, 60, vertraut=True),
    ),
    "einrichtung": (
        b("Pfleger", "Pflegerin", 70, vertraut=True),
        b("Arzt", "Ärztin", 15, vertraut=True),
        b("Angehöriger zu Besuch", "Angehörige zu Besuch", 15, vertraut=True),
    ),
    "oeffentlich": (
        b("Kollege", "Kollegin", 35, 16, 70),
        b("Mitarbeiter", "Mitarbeiterin", 30),
        b("Kunde", "Kundin", 25),
        b("Mitarbeiter des Sicherheitsdienstes", "Mitarbeiterin des Sicherheitsdienstes", 10),
    ),
    "schule": (
        b("Lehrer", "Lehrerin", 60, 0, 18),
        b("Mitschüler", "Mitschülerin", 25, 14, 25),
        b("Hausmeister", "Hausmeisterin", 15),
    ),
    "verkehr": (
        b("Passant", "Passantin", 55),
        b("Begleiter", "Begleiterin", 20),
        b("Fahrer", "Fahrerin", 15),
        b("Mitarbeiter des Sicherheitsdienstes", "Mitarbeiterin des Sicherheitsdienstes", 10),
    ),
    "draussen": (
        b("Passant", "Passantin", 45),
        b("Begleiter", "Begleiterin", 25),
        b("Vater", "Mutter", 20, 0, 17, vertraut=True),
        b("Trainer", "Trainerin", 10),
    ),
    "gewaesser": (
        b("Spaziergänger", "Spaziergängerin", 45),
        b("Rettungsschwimmer", "Rettungsschwimmerin", 30),
        b("Vater", "Mutter", 25, 0, 17, vertraut=True),
    ),
    "kultur": (
        b("Besucher", "Besucherin", 50),
        b("Mitarbeiter", "Mitarbeiterin", 30),
        b("Begleiter", "Begleiterin", 20),
    ),
    "betrieb": (
        b("Kollege", "Kollegin", 60, 16, 67),
        b("Vorarbeiter", "Vorarbeiterin", 25, 16, 67),
        b("Passant", "Passantin", 15),
    ),
    "geburt": (
        b("Partner", "Partnerin", 55, vertraut=True),
        b("Hebamme", "Hebamme", 20, vertraut=True),
        b("Vater", "Mutter", 15, 0, 45, vertraut=True),
        b("Freund", "Freundin", 10, vertraut=True),
    ),
    "neugeborenes": (
        b("Vater", "Mutter", 65, 0, 0, vertraut=True),
        b("Hebamme", "Hebamme", 20, vertraut=True),
        b("Großvater", "Großmutter", 15, 0, 0, vertraut=True),
    ),
}

ANGERUFEN = "Die Person hat dich angerufen; du bist nicht dort."
DRITTE_HAND = {
    "wohnung": (
        b("Sohn", "Tochter", 30, 38, vertraut=True, notiz=ANGERUFEN),
        b("Ehemann", "Ehefrau", 20, 20, vertraut=True, notiz=ANGERUFEN),
        b(
            "Mitarbeiter der Hausnotrufzentrale",
            "Mitarbeiterin der Hausnotrufzentrale",
            20,
            60,
            vertraut=True,
            notiz="Der Hausnotruf wurde ausgelöst, am Gerät meldet sich niemand.",
        ),
        b(
            "Hausmeister",
            "Hausmeisterin",
            10,
            vertraut=True,
            notiz="Mieter haben dir Hilferufe gemeldet; du kennst die Wohnung.",
        ),
        b(
            "Kollege",
            "Kollegin",
            10,
            16,
            67,
            notiz="Die Person ist nicht zur Arbeit gekommen und am Telefon kaum zu verstehen.",
        ),
        b(
            "Freund",
            "Freundin",
            10,
            14,
            notiz="Die Person hat dir eben geschrieben, dass es ihr schlecht geht.",
        ),
    ),
    "einrichtung": (
        b(
            "Arzt",
            "Ärztin",
            40,
            vertraut=True,
            notiz="Du hast die Person untersucht und weist sie ein.",
        ),
        b("Medizinischer Fachangestellter", "Medizinische Fachangestellte", 30, vertraut=True),
        b("Leiter der Einrichtung", "Leiterin der Einrichtung", 30, vertraut=True),
    ),
    "betrieb": (
        b(
            "Vorarbeiter",
            "Vorarbeiterin",
            60,
            16,
            67,
            notiz="Ein Kollege vor Ort hat dich angerufen; du bist im Büro.",
        ),
        b(
            "Kollege",
            "Kollegin",
            40,
            16,
            67,
            notiz="Ein Kollege vor Ort hat dich angerufen; du bist im Büro.",
        ),
    ),
    "schule": (
        b(
            "Mitarbeiter des Sekretariats",
            "Mitarbeiterin des Sekretariats",
            100,
            notiz="Eine Lehrkraft hat dich aus dem Gebäude angerufen.",
        ),
    ),
    "unterwegs": (
        b("Sohn", "Tochter", 30, 38, notiz="Die Person hat dich von unterwegs angerufen."),
        b("Ehemann", "Ehefrau", 25, 20, notiz="Die Person hat dich von unterwegs angerufen."),
        b("Vater", "Mutter", 20, 0, 17, notiz="Dein Kind hat dich von unterwegs angerufen."),
        b(
            "Freund",
            "Freundin",
            25,
            14,
            notiz="Die Person hat dir eben geschrieben, wo sie ist und dass es ihr schlecht geht.",
        ),
    ),
}
VIERTE_HAND = {
    "wohnung": (
        b("Nachbar", "Nachbarin", 70, notiz="Du hörst durch die Wand Schreie und Poltern."),
        b("Passant", "Passantin", 30, notiz="Du hörst im Vorbeigehen Hilferufe aus der Wohnung."),
    ),
    "unterwegs": (
        b("Passant", "Passantin", 70, notiz="Du siehst von weitem jemanden liegen."),
        b("Autofahrer", "Autofahrerin", 30, notiz="Du bist eben vorbeigefahren."),
    ),
}
DRINNEN = frozenset({"wohnung", "geburt", "neugeborenes"})
GEBAEUDE = frozenset({"betrieb", "oeffentlich", "einrichtung", "schule", "kultur"})
FEUERWEHR_ZWEITE = {
    "wohnung": (
        b("Nachbar", "Nachbarin", 40),
        b("Bewohner des Hauses", "Bewohnerin des Hauses", 30),
        b("Passant", "Passantin", 20),
        b("Hausmeister", "Hausmeisterin", 10),
    ),
    "betrieb": (b("Mitarbeiter", "Mitarbeiterin", 70), b("Passant", "Passantin", 30)),
    "oeffentlich": (
        b("Mitarbeiter", "Mitarbeiterin", 50),
        b("Besucher", "Besucherin", 30),
        b("Mitarbeiter des Sicherheitsdienstes", "Mitarbeiterin des Sicherheitsdienstes", 20),
    ),
    "verkehr": (
        b("Passant", "Passantin", 50),
        b("Autofahrer", "Autofahrerin", 35),
        b("Anwohner", "Anwohnerin", 15),
    ),
    "draussen": (b("Spaziergänger", "Spaziergängerin", 60), b("Anwohner", "Anwohnerin", 40)),
    "gewaesser": (b("Spaziergänger", "Spaziergängerin", 60), b("Angler", "Anglerin", 40)),
}
FEUERWEHR_DRITTE = {
    "wohnung": (
        b(
            "Mitarbeiter der Hausverwaltung",
            "Mitarbeiterin der Hausverwaltung",
            60,
            notiz="Ein Mieter hat dich angerufen.",
        ),
        b("Angehöriger", "Angehörige", 40, notiz="Jemand vor Ort hat dich angerufen."),
    ),
    "gebaeude": (
        b("Angehöriger", "Angehörige", 50, notiz="Jemand vor Ort hat dich angerufen."),
        b("Kollege", "Kollegin", 50, notiz="Ein Kollege vor Ort hat dich angerufen."),
    ),
    "draussen": (
        b("Angehöriger", "Angehörige", 50, notiz="Jemand vor Ort hat dich angerufen."),
        b("Bekannter", "Bekannte", 50, notiz="Ein Bekannter vor Ort hat dich angerufen."),
    ),
    "brandmeldeanlage": (
        b(
            "Mitarbeiter des Wachschutzes",
            "Mitarbeiterin des Wachschutzes",
            100,
            notiz="Die Meldung kam über die Aufschaltung.",
        ),
    ),
}
FEUERWEHR_VIERTE = {
    "brand-wohnung": (
        b("Nachbar", "Nachbarin", 40, notiz="Du riechst Rauch im Treppenhaus."),
        b("Nachbar", "Nachbarin", 30, notiz="Du hörst nebenan einen Rauchmelder piepen."),
        b("Passant", "Passantin", 30, notiz="Du siehst Rauch aus einem Fenster kommen."),
    ),
    "brand-gebaeude": (
        b("Passant", "Passantin", 60, notiz="Du siehst Rauch aus dem Gebäude kommen."),
        b("Anwohner", "Anwohnerin", 40, notiz="Du hörst aus dem Gebäude nebenan einen Alarm."),
    ),
    "brand-draussen": (
        b("Passant", "Passantin", 60, notiz="Du siehst von weitem Rauch aufsteigen."),
        b("Autofahrer", "Autofahrerin", 40, notiz="Du bist eben an Flammen vorbeigefahren."),
    ),
    "th-wohnung": (
        b("Nachbar", "Nachbarin", 70, notiz="Du hörst nebenan Hilferufe."),
        b("Passant", "Passantin", 30, notiz="Du hast im Vorbeigehen Rufe gehört."),
    ),
    "th-gebaeude": (
        b("Passant", "Passantin", 100, notiz="Du hast im Vorbeigehen Rufe aus dem Gebäude gehört."),
    ),
    "th-draussen": (
        b("Passant", "Passantin", 70, notiz="Du hast es im Vorbeigehen gesehen."),
        b("Autofahrer", "Autofahrerin", 30, notiz="Du bist eben vorbeigefahren."),
    ),
}
BRANDMELDEANLAGE = "fw.brand.brandmeldeanlage"
NOTFALL = {
    BEIM_BETROFFENEN: b("Passant", "Passantin", 1),
    FUER_ANDERE: b("Angehöriger", "Angehörige", 1, notiz="Jemand vor Ort hat dich angerufen."),
    GEHOERT: b("Passant", "Passantin", 1, notiz="Du hast es im Vorbeigehen gesehen."),
}


@dataclass(frozen=True)
class Gezogen:
    """A drawn relationship: how the caller names it, how they learned of it, what they know."""

    text: str = ""
    notiz: str = ""
    vertraut: bool = False


def beziehung_ziehen(
    hand: str,
    rahmen: str,
    alter: int | None,
    fachrichtung: str,
    protokoll: str,
    weiblich: bool,
    zufall: random.Random,
) -> Gezogen:
    """Draw the caller's relationship to the affected person, fitting hand, scene and age.

    `rahmen` is the frame of the scene (`ZWEITE_HAND` keys). A caller who is the person, or a
    system that reports by itself, has none. When no row fits the age, such as a child at a
    workplace, a passer-by or a relative stands in.
    """
    if hand in (SELBST, AUTOMATISCH):
        return Gezogen()
    zeilen = tabelle(hand, rahmen, fachrichtung, protokoll)
    passende = [z for z in zeilen if z.passt(alter)] or [NOTFALL[hand]]
    zeile = zufall.choices(passende, weights=[z.gewicht for z in passende])[0]
    return Gezogen(zeile.form(weiblich), zeile.notiz, zeile.vertraut)


def tabelle(hand: str, rahmen: str, fachrichtung: str, protokoll: str) -> tuple[Beziehung, ...]:
    """Return the rows a relationship is drawn from.

    Callers who are not there are told how they learned of it: at home through the wall or the
    house alarm, elsewhere from the person on the phone or from afar; a fire is smelt or seen.
    """
    drinnen = rahmen in DRINNEN
    if fachrichtung != "rd":
        return feuerwehr_tabelle(hand, rahmen, fachrichtung, protokoll)
    if hand == BEIM_BETROFFENEN:
        return ZWEITE_HAND.get(rahmen, ZWEITE_HAND["wohnung"])
    if hand == FUER_ANDERE:
        return DRITTE_HAND.get(rahmen, DRITTE_HAND["wohnung" if drinnen else "unterwegs"])
    return VIERTE_HAND["wohnung" if drinnen else "unterwegs"]


def feuerwehr_tabelle(
    hand: str, rahmen: str, fachrichtung: str, protokoll: str
) -> tuple[Beziehung, ...]:
    """Return the rows for a fire or technical rescue call."""
    gebaeude = rahmen in GEBAEUDE
    if hand == FUER_ANDERE:
        if protokoll == BRANDMELDEANLAGE:
            return FEUERWEHR_DRITTE["brandmeldeanlage"]
        if rahmen in DRINNEN:
            return FEUERWEHR_DRITTE["wohnung"]
        return FEUERWEHR_DRITTE["gebaeude" if gebaeude else "draussen"]
    if hand == GEHOERT:
        art = "brand" if fachrichtung == "brand" else "th"
        lage = "wohnung" if rahmen in DRINNEN else "gebaeude" if gebaeude else "draussen"
        return FEUERWEHR_VIERTE[f"{art}-{lage}"]
    return FEUERWEHR_ZWEITE.get(rahmen, FEUERWEHR_ZWEITE["wohnung"])


def altersbedingungen() -> dict[str, tuple[int, int]]:
    """Return, per relationship name, the widest ages of the affected person it fits."""
    bedingungen: dict[str, tuple[int, int]] = {}
    for zeilen in (*ZWEITE_HAND.values(), *DRITTE_HAND.values()):
        for zeile in zeilen:
            for weiblich in (False, True):
                von, bis = bedingungen.get(zeile.form(weiblich), (120, 0))
                bedingungen[zeile.form(weiblich)] = (min(von, zeile.von), max(bis, zeile.bis))
    return {name: spanne for name, spanne in bedingungen.items() if spanne != (0, 120)}


ALTERSBEDINGUNGEN = altersbedingungen()
