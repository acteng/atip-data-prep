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

    # https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dschool indicates
    # primary and secondary schools
    generatePolygonAmenity(args, "school", "schools")

    # Note https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dhospital doesn't
    # cover all types of medical facility
    generatePolygonAmenity(args, "hospital", "hospitals")


# Extract `amenity={amenity}` polygons from OSM, and only keep a name attribute.
def generatePolygonAmenity(args, amenity, filename):
    # Remove files from any previous run
    try:
        os.remove(f"{filename}.osm.pbf")
        os.remove(f"{filename}.geojson")
        os.remove(f"{filename}.pmtiles")
    except:
        pass

    # First extract a .osm.pbf with all amenity={name} features
    # TODO Do we need nwr? We don't want points further on
    run(
        [
            "osmium",
            "tags-filter",
            args.input,
            f"nwr/amenity={amenity}",
            "-o",
            f"{filename}.osm.pbf",
        ]
    )

    # Transform osm.pbf to GeoJSON, only keeping polygons. (Everything will be expressed as a MultiPolygon)
    run(
        [
            "osmium",
            "export",
            f"{filename}.osm.pbf",
            "--geometry-type=polygon",
            "-o",
            f"{filename}.geojson",
        ]
    )

    # Only keep one property
    remove_extra_properties(f"{filename}.geojson")

    # Convert to pmtiles. Default options are fine.
    run(["tippecanoe", f"{filename}.geojson", "-o", f"{filename}.pmtiles"])


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
