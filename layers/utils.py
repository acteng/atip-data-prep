import json
import os
import subprocess


def run(args):
    print(">", " ".join(args))
    subprocess.run(args, check=True)


def ensureEmptyTempDirectoryExists(directoryName):
    if os.path.isdir(directoryName):
        run(["rm", "-r", directoryName])
    os.makedirs(directoryName, exist_ok=True)


def convertPbfToGeoJson(pbfPath, geojsonPath, geometryType, includeOsmID=False):
    config = []
    if includeOsmID:
        # Created by `osmium export --print-default-config` and changing `id`
        # TODO We can do this with a CLI flag with newer osmium, but it's not
        # easy to install on Ubuntu 20
        config = ["--config", "osmium_with_ids.cfg"]

    run(
        [
            "osmium",
            "export",
            pbfPath,
            f"--geometry-type={geometryType}",
            "-o",
            geojsonPath,
        ]
        + config
    )


# Note the layer name is based on the output filename. This always generates
# numeric feature IDs. For autoZoom, see https://github.com/felt/tippecanoe docs about -zg.
def convertGeoJsonToPmtiles(geojsonPath, pmtilesPath, autoZoom=False, args=[]):
    layerName = os.path.basename(pmtilesPath)[: -len(".pmtiles")]
    zoom = []
    if autoZoom:
        zoom = ["-zg"]
    run(
        [
            "tippecanoe",
            geojsonPath,
            "--generate-ids",
            "-l",
            layerName,
            "-o",
            pmtilesPath,
        ]
        + zoom
        + args
    )


# Produces GeoJSON output
def reprojectToWgs84(inputPath, outputPath):
    run(
        [
            "ogr2ogr",
            "-f",
            "GeoJSON",
            outputPath,
            "-t_srs",
            "EPSG:4326",
            inputPath,
        ]
    )


# This method cleans up a GeoJSON file in a few ways, overwriting the path specified:
#
# - Removes redundant top-level attributes set by ogr2ogr
# - Filters features using filterFeatures
# - Adds a numeric ID to every feature
# - Trims coordinate precision
# - Uses the transformProperties callback to transform each feature's
#   properties. The callback takes input properties and should return output
#   properties.
def cleanUpGeojson(path, transformProperties, filterFeatures=lambda f: True):
    print(f"Cleaning up {path}")
    gj = {}
    with open(path) as f:
        gj = json.load(f)

        # Remove unnecessary attributes present in some files
        for key in ["name", "crs"]:
            if key in gj:
                del gj[key]

        gj["features"] = list(filter(filterFeatures, gj["features"]))

        counter = 1
        for feature in gj["features"]:
            feature["properties"] = transformProperties(feature["properties"])

            feature["geometry"]["coordinates"] = trimPrecision(
                feature["geometry"]["coordinates"]
            )

            # The frontend needs IDs for hovering
            feature["id"] = counter
            counter += 1
    with open(path, "w") as f:
        f.write(json.dumps(gj))


# Round coordinates to 6 decimal places. Takes feature.geometry.coordinates,
# handling any type.
def trimPrecision(data):
    if isinstance(data, list):
        return [trimPrecision(x) for x in data]
    elif isinstance(data, float):
        return round(data, 6)
    else:
        raise Exception(f"Unexpected data within coordinates: {data}")


# Modifies a GeoJSON file in-place, removing any holes from polygons.
def removePolygonHoles(path):
    gj = {}
    with open(path) as f:
        gj = json.load(f)
    for feature in gj["features"]:
        if feature["geometry"]["type"] != "Polygon":
            continue
        if len(feature["geometry"]["coordinates"]) > 1:
            print("Removing polygon holes from", feature["properties"])
            del feature["geometry"]["coordinates"][1:]
    with open(path, "w") as f:
        f.write(json.dumps(gj))
