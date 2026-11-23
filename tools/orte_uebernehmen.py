"""Derives the named places of Berlin from OpenStreetMap into `daten/orte/`.

The address list knows doors, not parks, stations, hospitals or allotment gardens. These come from
Geofabrik's daily Berlin extract of OpenStreetMap, listed on daten.berlin.de, under the Open
Database License. This tool reads the extract's shapefiles without any native library, keeps the
named objects of the classes a caller might name as a location, gives each a German kind, a point
(the centre of an area, the middle of a river's stretch) and the Ortsteil whose boundary holds it,
drops what lies outside Berlin, merges the stops and entrances that share a name close together
and the stretches of a river within one Ortsteil, and writes them to `orte.json.gz` with
`meta.json` beside it. The Ortsteil boundaries of OpenStreetMap carry the same 97 names as the
address list, so a place's Ortsteil reads as an address's does.

The result is committed through Git LFS and loaded by the server at startup; nothing is fetched
at runtime. Run it again and commit the result to refresh the places.

Usage: python tools/orte_uebernehmen.py [berlin-latest-free.shp.zip] [target folder]
"""

import gzip
import io
import json
import math
import re
import sys
import tempfile
import urllib.request
import zipfile
from collections.abc import Iterator
from pathlib import Path

import shapefile

QUELLE_URL = "https://download.geofabrik.de/europe/germany/berlin-latest-free.shp.zip"
LIZENZ = "Open Database License (ODbL) 1.0, © OpenStreetMap-Mitwirkende"
ZIEL = Path(__file__).resolve().parent.parent / "daten" / "orte"
ZUSAMMEN_METER = 400
LADEN_SEKUNDEN = 600
JE_ORTSTEIL = {"Fluss", "Kanal"}

ARTEN = {
    "pois": {
        "hospital": "Krankenhaus",
        "clinic": "Klinik",
        "nursing_home": "Pflegeheim",
        "school": "Schule",
        "kindergarten": "Kita",
        "college": "Hochschule",
        "university": "Universität",
        "police": "Polizei",
        "fire_station": "Feuerwache",
        "town_hall": "Rathaus",
        "courthouse": "Gericht",
        "prison": "Justizvollzugsanstalt",
        "embassy": "Botschaft",
        "consulate": "Konsulat",
        "library": "Bibliothek",
        "museum": "Museum",
        "theatre": "Theater",
        "cinema": "Kino",
        "arts_centre": "Kulturzentrum",
        "community_centre": "Gemeindezentrum",
        "attraction": "Sehenswürdigkeit",
        "castle": "Schloss",
        "fort": "Festung",
        "monument": "Denkmal",
        "tower": "Turm",
        "observation_tower": "Aussichtsturm",
        "viewpoint": "Aussichtspunkt",
        "water_tower": "Wasserturm",
        "windmill": "Windmühle",
        "fountain": "Brunnen",
        "zoo": "Zoo",
        "theme_park": "Freizeitpark",
        "stadium": "Stadion",
        "sports_centre": "Sportanlage",
        "sports_hall": "Sporthalle",
        "pitch": "Sportplatz",
        "swimming_pool": "Schwimmbad",
        "ice_rink": "Eisbahn",
        "golf_course": "Golfplatz",
        "playground": "Spielplatz",
        "park": "Park",
        "dog_park": "Hundeauslauf",
        "graveyard": "Friedhof",
        "camp_site": "Campingplatz",
        "mall": "Einkaufszentrum",
        "department_store": "Kaufhaus",
        "supermarket": "Supermarkt",
        "marketplace": "Markt",
        "hotel": "Hotel",
        "hostel": "Hostel",
        "post_office": "Postfiliale",
        "wastewater_plant": "Klärwerk",
        "water_works": "Wasserwerk",
        "biergarten": "Biergarten",
    },
    "transport": {
        "railway_station": "Bahnhof",
        "railway_halt": "Haltepunkt",
        "tram_stop": "Tramhaltestelle",
        "bus_stop": "Bushaltestelle",
        "bus_station": "Busbahnhof",
        "ferry_terminal": "Fähranleger",
        "airport": "Flughafen",
        "airfield": "Flugplatz",
        "helipad": "Hubschrauberlandeplatz",
    },
    "landuse": {
        "park": "Park",
        "cemetery": "Friedhof",
        "allotments": "Kleingartenanlage",
        "forest": "Wald",
        "recreation_ground": "Erholungsfläche",
        "meadow": "Wiese",
        "heath": "Heide",
        "nature_reserve": "Naturschutzgebiet",
    },
    "water": {"water": "Gewässer", "reservoir": "Becken", "riverbank": "Ufer"},
    "natural": {"beach": "Strand", "peak": "Berg"},
    "waterways": {"river": "Fluss", "canal": "Kanal"},
    "places": {"locality": "Ortslage", "hamlet": "Siedlung", "island": "Insel"},
}
GOTTESHAUS = {
    "christian": "Kirche",
    "muslim": "Moschee",
    "jewish": "Synagoge",
    "buddhist": "Tempel",
    "hindu": "Tempel",
    "sikh": "Gurdwara",
}
SCHICHT = re.compile(r"gis_osm_(?P<schicht>[a-z]+?)(_a)?_free_1\.shp$")


def main() -> None:
    """Read the extract given, or download today's, and write the places."""
    ziel = Path(sys.argv[2]) if len(sys.argv) > 2 else ZIEL
    if len(sys.argv) > 1:
        uebernehmen(Path(sys.argv[1]), ziel)
        return
    with tempfile.TemporaryDirectory() as ordner:
        datei = Path(ordner) / "berlin.shp.zip"
        print(f"Lade {QUELLE_URL} …")
        anfrage = urllib.request.Request(QUELLE_URL, headers={"User-Agent": "calltaker"})
        with (
            urllib.request.urlopen(anfrage, timeout=LADEN_SEKUNDEN) as antwort,
            datei.open("wb") as aus,
        ):
            while block := antwort.read(1 << 20):
                aus.write(block)
        uebernehmen(datei, ziel)


def uebernehmen(archiv: Path, ziel: Path) -> None:
    """Write the places of an extract to the target folder."""
    with zipfile.ZipFile(archiv) as zip_:
        ortsteile = ortsteile_lesen(zip_)
        orte = zusammenfassen(list(orte_lesen(zip_, ortsteile)))
        stand = stand_lesen(zip_)
    ziel.mkdir(parents=True, exist_ok=True)
    inhalt = json.dumps(orte, ensure_ascii=False, separators=(",", ":")).encode()
    with (
        (ziel / "orte.json.gz").open("wb") as roh,
        gzip.GzipFile(fileobj=roh, mode="wb", mtime=0) as aus,
    ):
        aus.write(inhalt)
    meta = {"quelle": QUELLE_URL, "stand": stand, "lizenz": LIZENZ, "anzahl": len(orte)}
    (ziel / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(f"{len(orte)} Orte, Stand {stand}, nach {ziel}")


def leser(zip_: zipfile.ZipFile, name: str) -> shapefile.Reader:
    """Open one layer of the archive in memory."""
    teile = {
        endung: io.BytesIO(zip_.read(name[:-4] + "." + endung)) for endung in ("shp", "shx", "dbf")
    }
    return shapefile.Reader(shp=teile["shp"], shx=teile["shx"], dbf=teile["dbf"], encoding="utf-8")


def ortsteile_lesen(zip_: zipfile.ZipFile) -> list[tuple[str, tuple, list[list]]]:
    """Return every Ortsteil with its bounding box and rings, from the administrative areas."""
    ortsteile = []
    for form, eintrag in eintraege(leser(zip_, "gis_osm_adminareas_a_free_1.shp")):
        if eintrag["fclass"] == "admin_level10" and eintrag["name"]:
            ortsteile.append((eintrag["name"], tuple(form.bbox), ringe(form)))
    return ortsteile


def eintraege(daten: shapefile.Reader) -> Iterator[tuple[shapefile.Shape, shapefile.Record]]:
    """Yield each object's shape and record, skipping the few objects without a geometry."""
    for stelle in range(len(daten)):
        try:
            form = daten.shape(stelle)
        except shapefile.ShapefileException:
            continue
        yield form, daten.record(stelle)


def ringe(form: shapefile.Shape) -> list[list]:
    """Return the rings of a shape as lists of (longitude, latitude)."""
    grenzen = [*form.parts, len(form.points)]
    return [form.points[a:b] for a, b in zip(grenzen, grenzen[1:], strict=False)]


def orte_lesen(zip_: zipfile.ZipFile, ortsteile: list) -> Iterator[list]:
    """Yield every named place of a kept class as [name, kind, Ortsteil, latitude, longitude]."""
    for name in sorted(zip_.namelist()):
        treffer = SCHICHT.search(name)
        if not treffer:
            continue
        schicht = treffer.group("schicht")
        if schicht not in ARTEN and schicht != "pofw":
            continue
        for form, eintrag in eintraege(leser(zip_, name)):
            art = art_von(schicht, eintrag["fclass"])
            if not art or not eintrag["name"] or not form.points:
                continue
            laenge, breite = punkt(form)
            ortsteil = ortsteil_von(ortsteile, laenge, breite)
            if ortsteil:
                yield [
                    " ".join(eintrag["name"].split()),
                    art,
                    ortsteil,
                    round(breite, 6),
                    round(laenge, 6),
                ]


def art_von(schicht: str, klasse: str) -> str | None:
    """Return the German kind of a class in a layer, or None for a class not kept."""
    if schicht == "pofw":
        return GOTTESHAUS.get(klasse.split("_")[0], "Gotteshaus")
    return ARTEN[schicht].get(klasse)


def punkt(form: shapefile.Shape) -> tuple[float, float]:
    """Return a shape's point: the point itself, the middle of a line, or an area's centre.

    An area's centre is that of its largest ring, so a park in several pieces is placed in its
    main piece.
    """
    if len(form.points) == 1:
        return form.points[0]
    if form.shapeType in (shapefile.POLYLINE, shapefile.POLYLINEZ, shapefile.POLYLINEM):
        return mitte(form.points)
    ring = max(ringe(form), key=lambda r: abs(flaeche_von(r)))
    flaeche = laenge = breite = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False):
        kreuz = x1 * y2 - x2 * y1
        flaeche += kreuz
        laenge += (x1 + x2) * kreuz
        breite += (y1 + y2) * kreuz
    if abs(flaeche) < 1e-12:
        xs, ys = zip(*ring, strict=True)
        return sum(xs) / len(xs), sum(ys) / len(ys)
    return laenge / (3 * flaeche), breite / (3 * flaeche)


def flaeche_von(ring: list) -> float:
    """Return a ring's signed area in square degrees, enough to compare rings."""
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False)) / 2


def mitte(punkte: list) -> tuple[float, float]:
    """Return the point halfway along a line."""
    strecken = [math.dist(a, b) for a, b in zip(punkte, punkte[1:], strict=False)]
    rest = sum(strecken) / 2
    for (a, b), laenge in zip(zip(punkte, punkte[1:], strict=False), strecken, strict=True):
        if rest <= laenge and laenge > 0:
            anteil = rest / laenge
            return a[0] + (b[0] - a[0]) * anteil, a[1] + (b[1] - a[1]) * anteil
        rest -= laenge
    return punkte[-1]


def ortsteil_von(ortsteile: list, laenge: float, breite: float) -> str:
    """Return the Ortsteil whose boundary holds a point, or an empty text outside all of them."""
    for name, (west, sued, ost, nord), alle in ortsteile:
        if west <= laenge <= ost and sued <= breite <= nord and innen(alle, laenge, breite):
            return name
    return ""


def innen(alle: list[list], x: float, y: float) -> bool:
    """Tell whether a point lies inside the rings, by the even-odd rule, so holes stay outside."""
    drin = False
    for ring in alle:
        for (x1, y1), (x2, y2) in zip(ring, [*ring[1:], ring[0]], strict=True):
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                drin = not drin
    return drin


def zusammenfassen(orte: list[list]) -> list[list]:
    """Keep one of the places that share name and kind within a few hundred metres, sorted by name.

    A stop has a pole per direction and a park can be both a point and an area; the caller names
    it once. A river or canal comes in many stretches and is kept once per Ortsteil it runs
    through, so "Spree, Moabit" and "Spree, Köpenick" stay apart.
    """
    behalten: dict[tuple[str, ...], list[list]] = {}
    for ort in sorted(orte, key=lambda o: (o[0].lower(), o[1], o[3], o[4])):
        je_ortsteil = ort[1] in JE_ORTSTEIL
        schluessel = (ort[0].lower(), ort[1], ort[2] if je_ortsteil else "")
        gleiche = behalten.setdefault(schluessel, [])
        if not (je_ortsteil and gleiche) and all(
            abstand(ort, anderer) > ZUSAMMEN_METER for anderer in gleiche
        ):
            gleiche.append(ort)
    return [ort for gleiche in behalten.values() for ort in gleiche]


def abstand(a: list, b: list) -> float:
    """Return the distance in metres between two places, close enough within a city."""
    breite = math.radians((a[3] + b[3]) / 2)
    dx = math.radians(a[4] - b[4]) * math.cos(breite)
    dy = math.radians(a[3] - b[3])
    return 6_371_000 * math.hypot(dx, dy)


def stand_lesen(zip_: zipfile.ZipFile) -> str:
    """Return the date of the data, as the extract's README states it."""
    treffer = re.search(r"as of (\S+)", zip_.read("README").decode())
    return treffer.group(1).rstrip(".") if treffer else ""


if __name__ == "__main__":
    main()
