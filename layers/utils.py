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


# Note the layer name is based on the input filename. This always generates
# numeric feature IDs.
def convertGeoJsonToPmtiles(geojsonPath, pmtilesPath):
    run(["tippecanoe", geojsonPath, "--generate-ids", "-o", pmtilesPath])


# Adds numeric IDs to every feature, trims coordinate precision, and uses the
# callback to transform each feature's properties. Overwrites the file.
#
# The callback takes (input properties, output properties) and doesn't return
# anything. Output is a blank dictionary that should be filled out.
def cleanUpGeojson(path, transformProperties):
    print(f"Cleaning up {path}")
    gj = {}
    with open(path) as f:
        gj = json.load(f)

        counter = 1
        for feature in gj["features"]:
            properties = {}
            transformProperties(feature["properties"], properties)
            feature["properties"] = properties

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
