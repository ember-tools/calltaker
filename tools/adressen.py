"""Loads the Berlin address list into the data folder, or reports what is there.

Run with `src` on the Python path, as `./toolchain.sh data-adressen` and `data-adressen-stand` do.

Usage: python tools/adressen.py laden|stand
"""

import sys

from adressen import Adressen
from einstellungen import einstellungen


def main() -> int:
    """Load the list or print its state, as the first argument asks."""
    adressen = Adressen(einstellungen().adressen_datei(), einstellungen().adressen_tage)
    if sys.argv[1:] == ["laden"]:
        print(f"{adressen.laden()} Adressen geladen nach {adressen.datei}")
        return 0
    if sys.argv[1:] == ["stand"]:
        print(adressen.bestand())
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
