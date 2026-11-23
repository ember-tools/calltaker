import gzip
import importlib.util
import io
import json
import zipfile
from pathlib import Path

import shapefile

WERKZEUG = Path(__file__).resolve().parent.parent / "tools" / "orte_uebernehmen.py"
spec = importlib.util.spec_from_file_location("orte_uebernehmen", WERKZEUG)
orte_uebernehmen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orte_uebernehmen)

MITTE = [[(13.0, 52.0), (13.1, 52.0), (13.1, 52.1), (13.0, 52.1), (13.0, 52.0)]]


def schicht(zip_, name, art, formen):
    teile = {endung: io.BytesIO() for endung in ("shp", "shx", "dbf")}
    schreiber = shapefile.Writer(
        shp=teile["shp"], shx=teile["shx"], dbf=teile["dbf"], shapeType=art, encoding="utf-8"
    )
    schreiber.field("fclass", "C", 28)
    schreiber.field("name", "C", 100)
    for klasse, titel, form in formen:
        zeichnen(schreiber, art, form)
        schreiber.record(klasse, titel)
    schreiber.close()
    for endung, inhalt in teile.items():
        zip_.writestr(f"{name}.{endung}", inhalt.getvalue())


def zeichnen(schreiber, art, form):
    if art == shapefile.POINT:
        schreiber.point(*form)
    elif art == shapefile.POLYLINE:
        schreiber.line(form)
    else:
        schreiber.poly(form)


def archiv_mit(tmp_path, **schichten):
    archiv = tmp_path / "berlin.shp.zip"
    with zipfile.ZipFile(archiv, "w") as zip_:
        zip_.writestr("README", "OpenStreetMap data as of 2026-11-22T21:20:48Z. Every day")
        schicht(zip_, "gis_osm_adminareas_a_free_1", shapefile.POLYGON, ORTSTEILE)
        for name, (art, formen) in schichten.items():
            schicht(zip_, f"gis_osm_{name}_free_1", art, formen)
    orte_uebernehmen.uebernehmen(archiv, tmp_path / "orte")
    return json.loads(gzip.decompress((tmp_path / "orte" / "orte.json.gz").read_bytes()))


LOCH = [(13.04, 52.04), (13.04, 52.06), (13.06, 52.06), (13.06, 52.04), (13.04, 52.04)]
ORTSTEILE = [
    ("admin_level10", "Mitte", [*MITTE, LOCH]),
    (
        "admin_level10",
        "Moabit",
        [[(13.1, 52.0), (13.2, 52.0), (13.2, 52.1), (13.1, 52.1), (13.1, 52.0)]],
    ),
]


def test_gotteshaeuser_loecher_arten_und_fluesse(tmp_path):
    orte = archiv_mit(
        tmp_path,
        pofw=(
            shapefile.POINT,
            [
                ("christian_protestant", "Dorfkirche", (13.01, 52.01)),
                ("zoroastrian", "Feuertempel", (13.02, 52.02)),
            ],
        ),
        pois=(
            shapefile.POINT,
            [
                ("park", "Im Loch", (13.05, 52.05)),
                ("park", "Zwilling", (13.03, 52.03)),
                ("playground", "Zwilling", (13.031, 52.031)),
                ("hospital", "Zeilen-\n  Umbruch", (13.03, 52.03)),
            ],
        ),
        waterways=(
            shapefile.POLYLINE,
            [
                ("river", "Spree", [[(13.01, 52.09), (13.03, 52.09)]]),
                ("river", "Spree", [[(13.03, 52.09), (13.05, 52.09)]]),
                ("river", "Spree", [[(13.15, 52.09), (13.17, 52.09)]]),
                ("stream", "Graben", [[(13.01, 52.08), (13.02, 52.08)]]),
            ],
        ),
    )
    assert [o[:3] for o in orte] == [
        ["Dorfkirche", "Kirche", "Mitte"],
        ["Feuertempel", "Gotteshaus", "Mitte"],
        ["Spree", "Fluss", "Mitte"],
        ["Spree", "Fluss", "Moabit"],
        ["Zeilen- Umbruch", "Krankenhaus", "Mitte"],
        ["Zwilling", "Park", "Mitte"],
        ["Zwilling", "Spielplatz", "Mitte"],
    ]
    assert orte[2][3:] == [52.09, 13.02]


def test_benannte_orte_mit_ortsteil_ohne_doppelte_haltestellen(tmp_path):
    archiv = tmp_path / "berlin.shp.zip"
    with zipfile.ZipFile(archiv, "w") as zip_:
        zip_.writestr("README", "OpenStreetMap data as of 2026-11-22T21:20:48Z. Every day")
        schicht(
            zip_,
            "gis_osm_adminareas_a_free_1",
            shapefile.POLYGON,
            [("admin_level10", "Mitte", MITTE)],
        )
        schicht(
            zip_,
            "gis_osm_pois_free_1",
            shapefile.POINT,
            [
                ("hospital", "Charité", (13.05, 52.05)),
                ("memorial", "Stolperstein", (13.05, 52.05)),
                ("hospital", "", (13.05, 52.05)),
                ("hospital", "Draußen", (14.0, 52.05)),
            ],
        )
        schicht(
            zip_,
            "gis_osm_transport_free_1",
            shapefile.POINT,
            [
                ("bus_stop", "U Mitte", (13.05, 52.05)),
                ("bus_stop", "U Mitte", (13.0505, 52.0501)),
                ("bus_stop", "U Mitte", (13.09, 52.09)),
            ],
        )
        schicht(
            zip_,
            "gis_osm_landuse_a_free_1",
            shapefile.POLYGON,
            [
                (
                    "allotments",
                    "KGA Sonnenschein",
                    [
                        [
                            (13.02, 52.02),
                            (13.04, 52.02),
                            (13.04, 52.04),
                            (13.02, 52.04),
                            (13.02, 52.02),
                        ]
                    ],
                ),
            ],
        )
    orte_uebernehmen.uebernehmen(archiv, tmp_path / "orte")
    orte = json.loads(gzip.decompress((tmp_path / "orte" / "orte.json.gz").read_bytes()))
    assert [o[:3] for o in orte] == [
        ["Charité", "Krankenhaus", "Mitte"],
        ["KGA Sonnenschein", "Kleingartenanlage", "Mitte"],
        ["U Mitte", "Bushaltestelle", "Mitte"],
        ["U Mitte", "Bushaltestelle", "Mitte"],
    ]
    assert orte[1][3:] == [52.03, 13.03]
    meta = json.loads((tmp_path / "orte" / "meta.json").read_text())
    assert meta["stand"] == "2026-11-22T21:20:48Z"
    assert meta["anzahl"] == 4
