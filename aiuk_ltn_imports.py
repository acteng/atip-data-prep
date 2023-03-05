#!/usr/bin/python3

import json
import os

os.mkdir("aiuk_boundaries")
with open("authorities.geojson") as f:
    gj = json.load(f)

    for feature in gj["features"]:
        if feature["properties"]["level"] == "LAD":
            name = feature["properties"]["name"]
            with open(f"aiuk_boundaries/{name}.geojson", "w") as f:
                f.write(json.dumps(feature))
