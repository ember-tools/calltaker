"""Checks the question graph in `daten/abfrage/` and prints what it holds.

Exit code 1 when the graph cannot be loaded or breaks a structural rule. Run with `src` on the
Python path, as `./toolchain.sh data-abfrage` does.

Usage: python tools/abfrage_pruefen.py [folder]
"""

import sys
from collections import Counter
from pathlib import Path

from abfrage import laden

VERZEICHNIS = Path(__file__).resolve().parent.parent / "daten" / "abfrage"


def main() -> int:
    """Load the graph and report its size, or its faults."""
    verzeichnis = Path(sys.argv[1]) if len(sys.argv) > 1 else VERZEICHNIS
    try:
        graph = laden(verzeichnis)
    except ValueError as fehler:
        print(f"Abfragegraph fehlerhaft:\n{fehler}", file=sys.stderr)
        return 1
    je_fachrichtung = Counter(endpunkt.fachrichtung for endpunkt in graph.endpunkte)
    codes = ", ".join(f"{name} {anzahl}" for name, anzahl in sorted(je_fachrichtung.items()))
    print(
        f"Abfragegraph Version {graph.meta.version}: {len(graph.knoten)} Knoten, "
        f"{len(graph.endpunkte)} Codes ({codes})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
