#!/usr/bin/python3

import json
from shapely.geometry import Point, Polygon, shape


def main():
    # This file came from https://datahub.io/core/geo-countries, then I manually clipped it down
    with open("uk.geojson") as f:
        uk: Polygon = shape(json.load(f)["features"][0]["geometry"])
        (x1, y1, x2, y2) = uk.bounds

        step_size = 0.1
        features = []
        x = x1
        while x < x2:
            y = y1
            while y < y2:
                # TODO Messes up along the edge
                if uk.contains(Point(x, y)):
                    features.append(
                        {
                            "type": "Feature",
                            "properties": {"id": str(len(features))},
                            "geometry": {
                                "coordinates": [
                                    [
                                        [x, y],
                                        [x + step_size, y],
                                        [x + step_size, y + step_size],
                                        [x, y + step_size],
                                        [x, y],
                                    ]
                                ],
                                "type": "Polygon",
                            },
                        }
                    )
                y += step_size
            x += step_size

    gj = {"type": "FeatureCollection", "features": features}
    geojsonToOsmiumExtracts(gj)


# See https://osmcode.org/osmium-tool/manual.html#creating-geographic-extracts
#
# Tune batch_size carefully. Too big, and one pass of osmium runs out of memory.
def geojsonToOsmiumExtracts(gj, batch_size=50, directory="/tmp/osmium_extract/"):
    num_batches = 0
    config = {"directory": directory, "extracts": []}

    for feature in gj["features"]:
        with open(feature["properties"]["id"] + ".geojson", "w") as f:
            f.write(json.dumps(feature))
        config["extracts"].append(
            {
                "output": feature["properties"]["id"] + ".osm",
                "polygon": {
                    "file_name": feature["properties"]["id"] + ".geojson",
                    "file_type": "geojson",
                },
            }
        )
        if len(config["extracts"]) == batch_size:
            with open("uk_tiles_" + str(num_batches) + ".json", "w") as f:
                f.write(json.dumps(config))
            config["extracts"] = []
            num_batches += 1

    with open("uk_tiles_" + str(num_batches) + ".json", "w") as f:
        f.write(json.dumps(config))


if __name__ == "__main__":
    main()
