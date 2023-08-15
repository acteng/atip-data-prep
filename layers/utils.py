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


def convertPbfToGeoJson(pbfPath, geojsonPath, geometryType):
    run(
        [
            "osmium",
            "export",
            pbfPath,
            f"--geometry-type={geometryType}",
            "-o",
            geojsonPath,
        ]
    )


# Note the layer name is based on the output filename. This always generates
# numeric feature IDs.
def convertGeoJsonToPmtiles(geojsonPath, pmtilesPath):
    layerName = os.path.basename(pmtilesPath)[: -len(".pmtiles")]
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
