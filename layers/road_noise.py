from utils import *


def makeRoadNoise():
    tmp = "tmp_road_noise"
    ensureEmptyTempDirectoryExists(tmp)

    # From https://environment.data.gov.uk/dataset/b9c6bf30-a02d-4378-94a0-2982de1bef86
    run(
        [
            "wget",
            "https://environment.data.gov.uk/api/file/download?fileDataSetId=9279738f-a766-4048-876e-e5f000463074&fileName=RoadNoiseLAeq16hRound3-GeoJSON.zip",
            "-O",
            f"{tmp}/input.zip",
        ]
    )
    run(["unzip", f"{tmp}/input.zip", "-d", tmp])

    # Note the JSON file isn't GeoJSON, but ogr2ogr manages to understand it
    reprojectToWgs84(
        f"{tmp}/data/Road_Noise_LAeq16h_England_Round_3.json",
        f"{tmp}/road_noise.geojson",
    )

    def fixProps(inputProps):
        return {
            "noiseclass": inputProps["noiseclass"],
        }

    cleanUpGeojson(f"{tmp}/road_noise.geojson", fixProps)
    convertGeoJsonToPmtiles(
        f"{tmp}/road_noise.geojson",
        f"output/road_noise.pmtiles",
    )
