import csv
from collections import defaultdict
from utils import *


def makeSRN():
    tmp = "tmp_srn"
    ensureEmptyTempDirectoryExists(tmp)

    run(
        [
            "wget",
            # From https://osdatahub.os.uk/downloads/open/OpenRoads
            "https://api.os.uk/downloads/v1/products/OpenRoads/downloads?area=GB&format=GeoPackage&redirect",
            "-O",
            f"{tmp}/oproad_gpkg_gb.zip",
        ]
    )
    run(["unzip", f"{tmp}/oproad_gpkg_gb.zip", "-d", tmp])

    # Convert to GeoJSON, projecting to WGS84. Select only trunk roads (the SRN).
    run(
        [
            "ogr2ogr",
            "-f",
            "GeoJSON",
            f"{tmp}/srn.geojson",
            "-t_srs",
            "EPSG:4326",
            f"{tmp}/Data/oproad_gb.gpkg",
            "-sql",
            "SELECT name_1 as name, geometry FROM road_link WHERE trunk_road",
        ]
    )

    convertGeoJsonToPmtiles(
        f"{tmp}/srn.geojson",
        "output/srn.pmtiles",
    )
