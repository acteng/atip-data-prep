#!/usr/bin/python3

import argparse
import json
import os
import subprocess


# This tool takes an England-wide osm.pbf (from
# http://download.geofabrik.de/europe/great-britain/england-latest.osm.pbf) and
# generates files with point-of-interest layers for ATIP.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Path to england-latest.osm.pbf file", type=str)
    args = parser.parse_args()

    generateSchools()


def generateSchools():
    # Remove files from any previous run
    try:
        os.remove("schools.osm.pbf")
        os.remove("schools.geojson")
    except:
        pass

    # https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dschool indicates
    # primary and secondary schools. First extract a .osm.pbf with these
    # TODO Do we need nwr? We don't want points further on
    run(
        [
            "osmium",
            "tags-filter",
            args.input,
            "nwr/amenity=school",
            "-o",
            "schools.osm.pbf",
        ]
    )

    # Transform osm.pbf to GeoJSON, only keeping polygons. (Everything will be expressed as a MultiPolygon)
    run(
        [
            "osmium",
            "export",
            "schools.osm.pbf",
            "--geometry-type=polygon",
            "-o",
            "schools.geojson",
        ]
    )

    # Only keep one property
    remove_extra_properties("schools.geojson")

    # Convert to pmtiles. Default options are fine.
    run(["tippecanoe", "schools.geojson", "-o", "schools.pmtiles"])


def run(args):
    print(">", " ".join(args))
    subprocess.run(args, check=True)


# For each GeoJSON feature, keep only the name attribute. Overwrites the given file.
def remove_extra_properties(path):
    print(f"Removing extra properties from {path}")
    gj = {}
    with open(path) as f:
        gj = json.load(f)
        for feature in gj["features"]:
            # Remove all properties except for "name"
            props = {}
            name = feature["properties"].get("name")
            if name:
                props["name"] = name
            feature["properties"] = props

    with open(path, "w") as f:
        f.write(json.dumps(gj))


if __name__ == "__main__":
    main()
