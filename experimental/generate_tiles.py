#!/usr/bin/python3
# Writes a GeoJSON file, with one feature per square tile covering the UK. The output has problems.

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
    with open("uk_tiles.geojson", "w") as f:
        f.write(json.dumps(gj))


if __name__ == "__main__":
    main()
