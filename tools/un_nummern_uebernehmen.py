"""Takes the list of UN numbers from chemie.de into `daten/gefahrstoffe/`.

The page carries the German Wikipedia's list under the GNU Free Documentation License. Every row
of its tables gives a UN number or a range of them, the hazard number, the class and the name;
ranges such as "0005 - 0007" become one entry per number, and classes written as "6-1" or "3."
are read as "6.1" and "3". Writes `un.json` with the entries and
`meta.json` with source, date, licence and where the authors are listed.

Usage: python tools/un_nummern_uebernehmen.py [saved page.html]
"""

import json
import re
import sys
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

QUELLE = "https://www.chemie.de/lexikon/Liste_der_UN-Nummern.html"
ZIEL = Path(__file__).resolve().parent.parent / "daten" / "gefahrstoffe"
NUMMER = re.compile(r"^(\d{4})(?:\s*-\s*(\d{4}))?$")


class Tabellenleser(HTMLParser):
    """Collects the text of every cell of the page's `prettytable` tables, row by row."""

    def __init__(self) -> None:
        """Start with no rows read."""
        super().__init__()
        self.zeilen: list[list[str]] = []
        self.in_tabelle = 0
        self.zelle: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Open tables, rows and cells."""
        if tag == "table":
            self.in_tabelle += (
                1 if self.in_tabelle or "prettytable" in (dict(attrs).get("class") or "") else 0
            )
        elif self.in_tabelle and tag == "tr":
            self.zeilen.append([])
        elif self.in_tabelle and tag == "td":
            self.zelle = []

    def handle_endtag(self, tag: str) -> None:
        """Close cells and tables."""
        if tag == "table" and self.in_tabelle:
            self.in_tabelle -= 1
        elif tag == "td" and self.zelle is not None:
            self.zeilen[-1].append(" ".join("".join(self.zelle).split()))
            self.zelle = None

    def handle_data(self, data: str) -> None:
        """Collect the text of the open cell."""
        if self.zelle is not None:
            self.zelle.append(data)


def eintraege(seite: str) -> list[dict[str, str]]:
    """Read the entries of the page, one per UN number, in the page's order within a number."""
    leser = Tabellenleser()
    leser.feed(seite)
    ergebnis = []
    for zeile in leser.zeilen:
        if len(zeile) != 4:
            continue
        nummer, gefahrenzahl, klasse, bezeichnung = zeile
        treffer = NUMMER.match(nummer)
        if not treffer or not bezeichnung:
            continue
        klasse = klasse.replace("-", ".").rstrip(".")
        von = int(treffer.group(1))
        bis = int(treffer.group(2) or von)
        ergebnis.extend(
            {
                "un": f"{un:04d}",
                "gefahrenzahl": gefahrenzahl,
                "klasse": klasse,
                "bezeichnung": bezeichnung,
            }
            for un in range(von, bis + 1)
        )
    return sorted(ergebnis, key=lambda eintrag: eintrag["un"])


def laden(argumente: list[str]) -> str:
    """Read a saved page, or fetch it from the source."""
    if argumente:
        return Path(argumente[0]).read_text("utf-8")
    anfrage = urllib.request.Request(QUELLE, headers={"User-Agent": "calltaker-daten"})
    with urllib.request.urlopen(anfrage, timeout=60) as antwort:
        return antwort.read().decode("utf-8")


def main() -> int:
    """Take the list and write it with its metadata."""
    liste = eintraege(laden(sys.argv[1:]))
    if len(liste) < 1000:
        print(
            f"Nur {len(liste)} Einträge gelesen, die Seite hat sich wohl geändert.", file=sys.stderr
        )
        return 1
    ZIEL.mkdir(parents=True, exist_ok=True)
    zeilen = ",\n".join(json.dumps(eintrag, ensure_ascii=False) for eintrag in liste)
    (ZIEL / "un.json").write_text(f"[\n{zeilen}\n]\n", "utf-8")
    meta = {
        "quelle": QUELLE,
        "ursprung": "https://de.wikipedia.org/wiki/Liste_der_UN-Nummern",
        "autoren": "https://de.wikipedia.org/w/index.php?title=Liste_der_UN-Nummern&action=history",
        "lizenz": "GNU-Lizenz für freie Dokumentation",
        "stand": date.today().isoformat(),
        "eintraege": len(liste),
    }
    (ZIEL / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"{len(liste)} Einträge nach {ZIEL} geschrieben")
    return 0


if __name__ == "__main__":
    sys.exit(main())
