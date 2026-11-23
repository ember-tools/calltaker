"""Street names that sound like or are spelled almost like what was typed.

Callers spell streets as they hear them and trainees type fast, so "Siegmartstrase" should still
find Siegmarstraße. Two tests decide whether a street comes close enough, both on the start of its
name, since the text is usually still being typed:

* **Phonetics:** the Kölner Phonetik code of the typed text begins the street's code, and both
  begin with the same letter or the same consonant sound. It reads German spelling by sound, so
  "Maier", "Meyer" and "Mayr" share a code.
* **Typos:** the typed text is at most one edit (two from eight letters on) from a start of the
  street name, counting a swap of two neighbouring letters as one edit.

Both are compared on a normal form: lower case, "ß" as "ss", "str"/"str." spelled out, and only
letters and digits kept. A street is only tried when its first letter matches, which keeps the
typo test cheap over the ten thousand street names of Berlin.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

STRASSE = re.compile(r"str\.?(?=\s|$)|strasse|straße")
NICHT_WORT = re.compile(r"[^a-z0-9äöü]+")
MINDESTLAENGE = 4
LANG = 8

KOELN = {
    **dict.fromkeys("aeijouyäöü", "0"),
    "h": "",
    "b": "1",
    "f": "3",
    "v": "3",
    "w": "3",
    **dict.fromkeys("gkq", "4"),
    "l": "5",
    **dict.fromkeys("mn", "6"),
    "r": "7",
    **dict.fromkeys("sz", "8"),
}


@dataclass(frozen=True)
class Name:
    """A street name with the forms it is compared in."""

    name: str
    normal: str
    phonetik: str


def normal(text: str) -> str:
    """Return a name in the form it is compared in."""
    klein = text.lower().replace("ß", "ss")
    return NICHT_WORT.sub("", STRASSE.sub("strasse", klein))


def phonetik(text: str) -> str:
    """Return the Kölner Phonetik code of a text: digits for sounds, vowels only at the start."""
    zeichen = normal(text).replace("ä", "a").replace("ö", "o").replace("ü", "u")
    roh = [laut(zeichen, stelle) for stelle in range(len(zeichen))]
    code = ""
    for wert in roh:
        if wert and (not code or code[-1] != wert[0]):
            code += wert
        elif wert and len(wert) > 1:
            code += wert[1:]
    return code[0] + code[1:].replace("0", "") if code else ""


def laut(zeichen: str, stelle: int) -> str:
    """Return the code of one letter, which for some letters depends on its neighbours."""
    buchstabe = zeichen[stelle]
    vorher = zeichen[stelle - 1] if stelle else ""
    nachher = zeichen[stelle + 1] if stelle + 1 < len(zeichen) else ""
    if buchstabe in "dt":
        return "8" if nachher in "csz" else "2"
    if buchstabe == "p":
        return "3" if nachher == "h" else "1"
    if buchstabe == "x":
        return "8" if vorher in "ckq" else "48"
    if buchstabe == "c":
        if stelle == 0:
            return "4" if nachher in "ahkloqrux" else "8"
        return "8" if vorher in "sz" or nachher not in "ahkoqux" else "4"
    if buchstabe.isdigit():
        return ""
    return KOELN.get(buchstabe, "")


def abstand(a: str, b: str, grenze: int) -> int:
    """Return the edit distance of two texts, a swap of neighbours counting once, or grenze + 1."""
    if abs(len(a) - len(b)) > grenze:
        return grenze + 1
    vorvorher: list[int] = []
    vorher = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        zeile = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            kosten = 0 if a[i - 1] == b[j - 1] else 1
            zeile[j] = min(vorher[j] + 1, zeile[j - 1] + 1, vorher[j - 1] + kosten)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                zeile[j] = min(zeile[j], vorvorher[j - 2] + 1)
        if min(zeile) > grenze:
            return grenze + 1
        vorvorher, vorher = vorher, zeile
    return vorher[-1]


def namen(strassen: Iterable[str]) -> list[Name]:
    """Return street names with their compared forms, for repeated searches."""
    return [Name(strasse, normal(strasse), phonetik(strasse)) for strasse in strassen]


def aehnliche(alle: list[Name], text: str, hoechstens: int = 8) -> list[str]:
    """Return the streets that sound or are spelled almost like the start typed, closest first."""
    gesucht = normal(text)
    if len(gesucht) < MINDESTLAENGE:
        return []
    klang = phonetik(text)
    grenze = 2 if len(gesucht) >= LANG else 1
    treffer: list[tuple[int, str]] = []
    for eintrag in alle:
        if eintrag.normal.startswith(gesucht):
            continue
        tipp = (
            tippabstand(gesucht, eintrag.normal, grenze)
            if eintrag.normal[:1] == gesucht[:1]
            else grenze + 1
        )
        if tipp <= grenze:
            treffer.append((tipp, eintrag.name))
        elif (
            len(klang) >= 2
            and gleicher_anlaut(gesucht, eintrag.normal)
            and eintrag.phonetik.startswith(klang)
        ):
            treffer.append((grenze + 1, eintrag.name))
    treffer.sort()
    return [name for _, name in treffer[:hoechstens]]


def gleicher_anlaut(a: str, b: str) -> bool:
    """Tell whether two names begin alike: the same letter, or consonants of the same sound."""
    if a[:1] == b[:1]:
        return True
    anfang_a, anfang_b = laut(a, 0), laut(b, 0)
    return anfang_a == anfang_b and anfang_a not in ("", "0")


def tippabstand(gesucht: str, name: str, grenze: int) -> int:
    """Return how far the typed start lies from the closest start of a name."""
    return min(
        abstand(gesucht, name[:laenge], grenze)
        for laenge in range(max(1, len(gesucht) - grenze), len(gesucht) + grenze + 1)
    )
