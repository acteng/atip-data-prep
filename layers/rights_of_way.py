import json
import os
from utils import *


def makeRoW():
    tmp = "tmp_rights_of_way"
    ensureEmptyTempDirectoryExists(tmp)

    # Scrape https://www.rowmaps.com/jsons/. Manually uncomment and run with
    # caution; do not overload their server.
    if False:
        run(
            [
                "wget",
                "--recursive",
                "https://www.rowmaps.com/jsons/",
                "--level",
                "2",
                "--no-parent",
                "--random-wait",
                "--wait",
                "1",
                "--reject",
                "'*.zip'",
            ]
        )

    output = {
        "type": "FeatureCollection",
        "features": [],
    }

    # Walk through the directory of downloaded files
    root_dir = "rowmaps/www.rowmaps.com/jsons"
    for dir_name in os.listdir(root_dir):
        if dir_name == "index.html":
            continue
        for filename in os.listdir(os.path.join(root_dir, dir_name)):
            if filename.startswith("mutated") and filename.endswith(".json"):
                with open(os.path.join(root_dir, dir_name, filename)) as f:
                    gj = json.load(f)

                    # Copy features over, overwriting properties
                    for f in gj["features"]:
                        f["properties"] = {
                            "kind": {
                                "mutated1.json": "footpath",
                                "mutated2.json": "bridleway",
                                "mutated3.json": "restricted byway",
                                "mutated4.json": "byway open to all traffic",
                            }[filename]
                        }
                    output["features"].extend(gj["features"])

    with open(f"{tmp}/rights_of_way.geojson", "w") as f:
        f.write(json.dumps(output))
    convertGeoJsonToPmtiles(
        f"{tmp}/rights_of_way.geojson",
        "output/rights_of_way.pmtiles",
        autoZoom=True,
        args=["--drop-densest-as-needed"],
    )
