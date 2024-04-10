import json

from utils import *


def makeCrossings(osm_input):
    if not osm_input:
        raise Exception("You must specify --osm_input")

    tmp = "tmp_crossings"
    ensureEmptyTempDirectoryExists(tmp)

    run(
        [
            "osmium",
            "tags-filter",
            osm_input,
            "nw/highway,footway,cycleway=crossing",
            "-o",
            f"{tmp}/crossings.osm.pbf",
        ]
    )
    convertPbfToGeoJson(
        f"{tmp}/crossings.osm.pbf",
        f"{tmp}/raw_crossings.geojson",
        "point,linestring",
        includeOsmID=True,
        attributes="way_nodes",
    )

    # Crossings can be represented by a way, a node, or both. When it's both, group them together.
    nodes = {}
    ways = {}
    with open(f"{tmp}/raw_crossings.geojson") as f:
        gj = json.load(f)
        for f in gj["features"]:
            if "@way_nodes" in f["properties"]:
                ways[f["properties"]["@id"]] = f
            else:
                nodes[f["properties"]["@id"]] = f

    combined = []
    for way in ways.values():
        for node_id in way["properties"]["@way_nodes"]:
            if node_id in nodes:
                # A way usually only has one crossing node as a member. Just
                # overwrite, in the rare case of there being multiple.
                way["properties"]["@crossing_node"] = nodes[node_id]["properties"]
                del nodes[node_id]
        combined.append(way)
    for node in nodes.values():
        combined.append(node)

    counter = 1
    for f in combined:
        f["geometry"]["coordinates"] = trimPrecision(f["geometry"]["coordinates"])
        f["id"] = counter
        counter += 1

    # TODO Transform the properties. There are many combinations to think through.

    with open(f"{tmp}/crossings.geojson", "w") as f:
        f.write(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": combined,
                }
            )
        )
