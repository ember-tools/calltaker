"""Made-up callers and numbers for scenarios.

Scenarios are written for practice, not from real calls, so their personal details are generated
rather than typed. The names are meant to look like the people who actually ring the Berlin fire
brigade: roughly a quarter of Berlin holds a non-German passport and about a third of the city has
a migration background, the largest groups being Turkish, Ukrainian, Polish, Syrian, Vietnamese and
Indian. The weights reflect that shape as a plausible mix, not a distribution derived from the
registry. First and last name come from the same group, and Polish surnames take their feminine
form for women. The lists follow alarmzettel's generator.
"""

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Namensgruppe:
    """One group of names: its weight, given names with their gender, and surnames."""

    gewicht: int
    vornamen: tuple[tuple[str, bool], ...]
    nachnamen: tuple[str | tuple[str, str], ...]


def _m(*namen: str) -> tuple[tuple[str, bool], ...]:
    """Return male given names."""
    return tuple((name, False) for name in namen)


def _w(*namen: str) -> tuple[tuple[str, bool], ...]:
    """Return female given names."""
    return tuple((name, True) for name in namen)


NAMENSGRUPPEN = (
    Namensgruppe(
        68,
        _m("Michael", "Thomas", "Andreas", "Frank", "Peter", "Uwe", "Manfred", "Hartmut", "Jörg")
        + _m("Christian", "Stefan", "Sebastian", "Daniel", "Tobias", "Lukas", "Paul", "Leon")
        + _m("Jonas", "Felix")
        + _w("Sabine", "Petra", "Renate", "Christa", "Kerstin", "Ines", "Anke", "Susanne")
        + _w("Claudia", "Nicole", "Anja", "Julia", "Katrin", "Stefanie", "Laura", "Hannah")
        + _w("Emma", "Mia", "Marie"),
        (
            "Müller",
            "Schmidt",
            "Schneider",
            "Fischer",
            "Weber",
            "Meyer",
            "Wagner",
            "Schulz",
            "Bauer",
            "Becker",
            "Hoffmann",
            "Koch",
            "Klein",
            "Richter",
            "Wolf",
            "Schwarz",
            "Neumann",
            "Schröder",
            "Braun",
            "Zimmermann",
            "Krüger",
            "Hartmann",
            "Werner",
            "Lange",
            "Lehmann",
            "König",
            "Kaiser",
            "Krause",
            "Schulze",
            "Winkler",
            "Sommer",
        ),
    ),
    Namensgruppe(
        9,
        _m("Mehmet", "Mustafa", "Ali", "Hasan", "Emre", "Murat", "Yusuf", "Kerem")
        + _w("Ayşe", "Fatma", "Emine", "Zeynep", "Elif", "Leyla", "Merve"),
        ("Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Yıldız", "Öztürk", "Aydın", "Arslan"),
    ),
    Namensgruppe(
        6,
        _m("Oleksandr", "Serhij", "Andrij", "Dmytro", "Wolodymyr")
        + _w("Olena", "Natalija", "Iryna", "Oksana", "Kateryna"),
        ("Melnyk", "Kowalenko", "Schewtschenko", "Bondarenko", "Tkatschuk", "Boyko", "Kravets"),
    ),
    Namensgruppe(
        5,
        _m("Piotr", "Tomasz", "Marek", "Krzysztof", "Andrzej")
        + _w("Agnieszka", "Katarzyna", "Małgorzata", "Magdalena", "Joanna"),
        (
            "Nowak",
            "Wójcik",
            "Mazur",
            "Kaczmarek",
            ("Kowalski", "Kowalska"),
            ("Wiśniewski", "Wiśniewska"),
            ("Kamiński", "Kamińska"),
            ("Lewandowski", "Lewandowska"),
        ),
    ),
    Namensgruppe(
        5,
        _m("Ahmad", "Omar", "Mohammed", "Khaled", "Yassin", "Bilal")
        + _w("Fatima", "Layla", "Nour", "Rania", "Amina"),
        ("Haddad", "Khalil", "Hassan", "Ibrahim", "Saleh", "Nasser", "Aziz", "Darwisch"),
    ),
    Namensgruppe(
        4,
        _m("Minh", "Tuan", "Duc", "Hieu", "Long") + _w("Lan", "Mai", "Thuy", "Huong", "Ngoc"),
        ("Nguyen", "Tran", "Pham", "Le", "Hoang", "Vu", "Dang"),
    ),
    Namensgruppe(
        3,
        _m("Rahul", "Amit", "Arjun", "Vikram", "Rohit")
        + _w("Priya", "Neha", "Ananya", "Divya", "Kavya"),
        ("Kumar", "Singh", "Sharma", "Patel", "Gupta", "Reddy", "Nair", "Verma"),
    ),
)

MOBILVORWAHLEN = ("151", "152", "157", "160", "162", "163", "170", "171", "175", "176")


def zufallsname(zufall: random.Random, weiblich: bool | None = None) -> str:
    """Return a full name from one group, optionally of the given gender."""
    gruppe = zufall.choices(NAMENSGRUPPEN, weights=[h.gewicht for h in NAMENSGRUPPEN])[0]
    vornamen = [v for v in gruppe.vornamen if weiblich is None or v[1] == weiblich]
    vorname, ist_weiblich = zufall.choice(vornamen)
    nachname = zufall.choice(gruppe.nachnamen)
    if isinstance(nachname, tuple):
        nachname = nachname[1] if ist_weiblich else nachname[0]
    return f"{vorname} {nachname}"


def festnetznummer(zufall: random.Random) -> str:
    """Return a Berlin landline number as digits with the country code."""
    return "4930" + _ziffern(zufall, 8)


def mobilnummer(zufall: random.Random) -> str:
    """Return a German mobile number as digits with the country code."""
    return "49" + zufall.choice(MOBILVORWAHLEN) + _ziffern(zufall, 7)


def _ziffern(zufall: random.Random, anzahl: int) -> str:
    """Return the given number of random digits."""
    return "".join(str(zufall.randrange(10)) for _ in range(anzahl))
