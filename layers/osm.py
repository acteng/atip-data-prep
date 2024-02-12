from utils import *


# Extract polygons from OSM using a tag filter, and only keep a name attribute.
def generatePolygonLayer(osm_input, tagFilter, filename):
    if not osm_input:
        raise Exception("You must specify --osm_input")

    tmp = f"tmp_{filename}"
    ensureEmptyTempDirectoryExists(tmp)

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

    cleanUpGeojson(f"{tmp}/{filename}.geojson", onlyKeepName)

    convertGeoJsonToPmtiles(f"{tmp}/{filename}.geojson", f"output/{filename}.pmtiles")

# Extract polygons from OSM using a tag filter, and only keep a name attribute.
def makeEducationLayer(osm_input):
    if not osm_input:
        raise Exception("You must specify --osm_input")
    filename = "education"
    tagFilter = "amenity=school,college,university"

    tmp = f"tmp_{filename}"
    ensureEmptyTempDirectoryExists(tmp)

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

    def cleanUpFeature(inputProps):
        outputProps = {}
        name = inputProps.get("name")
        type = inputProps.get("amenity")
        if name:
            outputProps["name"] = name
        if type:
            outputProps["type"] = type
        return outputProps



    cleanUpGeojson(f"{tmp}/{filename}.geojson", cleanUpFeature)

    convertGeoJsonToPmtiles(f"{tmp}/{filename}.geojson", f"output/{filename}.pmtiles")



def onlyKeepName(inputProps):
    outputProps = {}
    name = inputProps.get("name")
    if name:
        outputProps["name"] = name
    return outputProps


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

    cleanUpGeojson(outputFilepath, onlyKeepName)


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

    def fixProps(inputProps):
        outputProps = {}
        if roadHasBusLane(inputProps):
            outputProps["has_bus_lane"] = True
        return outputProps

    cleanUpGeojson(f"{tmp}/{filename}.geojson", fixProps)

    convertGeoJsonToPmtiles(f"{tmp}/{filename}.geojson", f"output/{filename}.pmtiles")


def makeCycleParking(osm_input):
    if not osm_input:
        raise Exception("You must specify --osm_input")

    filename = "cycle_parking"
    tmp = f"tmp_{filename}"
    ensureEmptyTempDirectoryExists(tmp)

    # See https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dbicycle_parking
    run(
        [
            "osmium",
            "tags-filter",
            osm_input,
            "n/amenity=bicycle_parking",
            "-o",
            f"{tmp}/extract.osm.pbf",
        ]
    )
    convertPbfToGeoJson(f"{tmp}/extract.osm.pbf", f"{tmp}/{filename}.geojson", "point")

    def fixProps(inputProps):
        outputProps = {}
        try:
            outputProps["capacity"] = int(inputProps.get("capacity"))
        except:
            # Ignore parsing errors and missing values
            pass
        return outputProps

    cleanUpGeojson(f"{tmp}/{filename}.geojson", fixProps)

    convertGeoJsonToPmtiles(
        f"{tmp}/{filename}.geojson", f"output/{filename}.pmtiles", autoZoom=True
    )


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


def makeCrossings(
    osm_input,
):
    if not osm_input:
        raise Exception("You must specify --osm_input")

    filename = "crossings"
    tmp = f"tmp_{filename}"
    ensureEmptyTempDirectoryExists(tmp)
    osmFilePath = f"{tmp}/extract.osm.pbf"
    run(
        [
            "osmium",
            "tags-filter",
            osm_input,
            "n/crossing",
            "-o",
            osmFilePath,
        ]
    )
    tmpGeojsonFilepath = f"{tmp}/{filename}.geojson"
    outputFilepath = f"output/{filename}.pmtiles"
    convertPbfToGeoJson(osmFilePath, tmpGeojsonFilepath, "point", includeOsmID=True)

    def fixProps(inputProps):
        outputProps = {}
        try:
            outputProps["osm_id"] = inputProps["@id"]
            outputProps["crossing"] = inputProps["crossing"]
        except:
            # Ignore parsing errors and missing values
            pass
        return outputProps

    cleanUpGeojson(tmpGeojsonFilepath, fixProps)
    convertGeoJsonToPmtiles(tmpGeojsonFilepath, outputFilepath, autoZoom=True)


def makeTrams(osm_input):
    if not osm_input:
        raise Exception("You must specify --osm_input")

    filename = "trams"
    tmp = f"tmp_{filename}"
    ensureEmptyTempDirectoryExists(tmp)

    run(
        [
            "osmium",
            "tags-filter",
            osm_input,
            # Manchester's trams are tagged as light_rail
            "nwr/railway=tram,light_rail",
            "-o",
            f"{tmp}/extract.osm.pbf",
        ]
    )
    convertPbfToGeoJson(
        f"{tmp}/extract.osm.pbf",
        f"{tmp}/{filename}.geojson",
        "linestring",
        includeOsmID=True,
    )

    def fixProps(inputProps):
        return {
            "osm_id": inputProps["@id"],
        }

    cleanUpGeojson(f"{tmp}/{filename}.geojson", fixProps)

    convertGeoJsonToPmtiles(f"{tmp}/{filename}.geojson", f"output/{filename}.pmtiles")
