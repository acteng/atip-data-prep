#!/usr/bin/python3
# Writes a .geojson file for every LAD authority. This was used to import many areas into A/B Street for AI:UK.

import json
import os

os.mkdir("aiuk_boundaries")
with open("../authorities.geojson") as f:
    gj = json.load(f)

    for feature in gj["features"]:
        if feature["properties"]["level"] == "LAD":
            name = feature["properties"]["name"].replace(" ", "_").replace("-", "_").replace("'", "")
            with open(f"aiuk_boundaries/{name}.geojson", "w") as f:
                f.write(json.dumps(feature))
