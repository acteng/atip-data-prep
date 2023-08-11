from utils import *

# Extract polygons from OSM using a tag filter, and only keep a name attribute.
def generatePolygonLayer(osm_input, tagFilter, filename):
    if not osm_input:
        raise Exception("You must specify --osm_input")

    tmp = f"tmp_{filename}"
    ensureEmptyTempDirectoryExists(tmp)

    # First extract a .osm.pbf with all {tagPartOne}={tagPartTwo} features
    # TODO Do we need nwr? We don't want points further on
    run(
        [
            "osmium",
            "tags-filter",
            osm_input,
            f"nwr/{tagFilter}",
            "-o",
            f"{tmp}/extract.osm.pbf",
        ]
    )

    convertPbfToGeoJson(
        f"{tmp}/extract.osm.pbf", f"{tmp}/{filename}.geojson", "polygon"
    )

    cleanUpGeojson(f"{tmp}/{filename}.geojson", ["name"])

    convertGeoJsonToPmtiles(f"{tmp}/{filename}.geojson", f"output/{filename}.pmtiles")


def makeRailwayStations(
    osm_input,
):
    if not osm_input:
        raise Exception("You must specify --osm_input")

    filename = "railway_stations"
    tmp = f"tmp_{filename}"
    ensureEmptyTempDirectoryExists(tmp)
    osmFilePath = f"{tmp}/extract.osm.pbf"
    run(
        [
            "osmium",
            "tags-filter",
            osm_input,
            "n/railway=station",
            "-o",
            osmFilePath,
        ]
    )
    outputFilepath = f"output/{filename}.geojson"
    convertPbfToGeoJson(osmFilePath, outputFilepath, "point")

    cleanUpGeojson(outputFilepath, ["name"])


def makeBusRoutes(osm_input):
    if not osm_input:
        raise Exception("You must specify --osm_input")

    filename = "bus_routes"
    tmp = f"tmp_{filename}"
    ensureEmptyTempDirectoryExists(tmp)

    # Bus routes are represented as relations. Note many routes cross the same
    # way, but osmium only outputs the way once when we export to GeoJSON
    run(
        [
            "osmium",
            "tags-filter",
            osm_input,
            "r/route=bus",
            "-o",
            f"{tmp}/extract.osm.pbf",
        ]
    )
    # The relations also include stop positions as points. Only keep
    # LineStrings, representing roads.
    convertPbfToGeoJson(
        f"{tmp}/extract.osm.pbf", f"{tmp}/{filename}.geojson", "linestring"
    )

    print(f"Cleaning up {tmp}/{filename}.geojson")
    gj = {}
    with open(f"{tmp}/{filename}.geojson") as f:
        gj = json.load(f)

        for feature in gj["features"]:
            # The GeoJSON has OSM ways representing roads on a bus route.
            # Remove all attributes from them, replacing with a boolean
            # has_bus_lane.
            properties = {}
            if roadHasBusLane(feature["properties"]):
                properties["has_bus_lane"] = True
            feature["properties"] = properties

            feature["geometry"]["coordinates"] = trimPrecision(
                feature["geometry"]["coordinates"]
            )
    with open(f"{tmp}/{filename}.geojson", "w") as f:
        f.write(json.dumps(gj))

    convertGeoJsonToPmtiles(f"{tmp}/{filename}.geojson", f"output/{filename}.pmtiles")


# Using the tags from an OSM way, determine if this road has bus lanes in any direction.
def roadHasBusLane(tags):
    # Per https://wiki.openstreetmap.org/wiki/Bus_lanes, there are many
    # different ways to indicate bus lanes in OSM. Return true if any match.

    # Handle https://wiki.openstreetmap.org/wiki/Key:busway
    for key in ["busway", "busway:both", "busway:right", "busway:left"]:
        value = tags.get(key)
        if value == "lane" or value == "opposite_lane":
            return True

    # Handle https://wiki.openstreetmap.org/wiki/Key:lanes:psv and
    # https://wiki.openstreetmap.org/wiki/Key:*:lanes
    for prefix in ["lanes:psv", "lanes:bus"]:
        for direction in ["", ":forward", ":backward"]:
            value = tags.get(prefix + direction)
            if value and value != "0":
                return True

    # Handle the per-lane restrictions
    for prefix in ["psv:lanes", "bus:lanes"]:
        for direction in ["", ":forward", ":backward"]:
            # https://wiki.openstreetmap.org/wiki/Key:access#Lane_dependent_restrictions
            # The value specifies access per lane. We don't care about
            # specifically where the bus lane is, just presence, so we don't
            # need to fully parse it.
            value = tags.get(prefix + direction)
            if value and "designated" in value:
                return True

    # Handle https://wiki.openstreetmap.org/wiki/Tag:access=no
    if tags.get("access") == "no":
        for key in ["bus", "psv"]:
            value = tags.get(key)
            if value == "yes" or value == "designated":
                return True

    # We're not handling highway=busway or other cases for service roads
    # designed exclusively for buses, because they're not intended for cyclists
    # or any other users.

    return False
