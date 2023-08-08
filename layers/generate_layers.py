#!/usr/bin/python3

import argparse
import csv
import json
import os
import subprocess


def main():
    parser = argparse.ArgumentParser()
    # Possible outputs to generate
    parser.add_argument("--schools", action="store_true")
    parser.add_argument("--hospitals", action="store_true")
    parser.add_argument("--mrn", action="store_true")
    parser.add_argument("--parliamentary_constituencies", action="store_true")
    parser.add_argument("--railway_stations", action="store_true")
    parser.add_argument("--sports_spaces", action="store_true")
    parser.add_argument(
        "--wards",
        help="Path to the manually downloaded Wards_(May_2023)_Boundaries_UK_BGC.geojson",
        type=str,
    )
    parser.add_argument("--combined_authorities", action="store_true")
    parser.add_argument("--local_authority_districts", action="store_true")
    parser.add_argument(
        "--census_output_areas",
        help="Path to the manually downloaded Output_Areas_2021_EW_BGC_V2_-3080813486471056666.geojson",
        type=str,
    )
    # Inputs required for some outputs
    parser.add_argument(
        "-i", "--osm_input", help="Path to england-latest.osm.pbf file", type=str
    )
    args = parser.parse_args()

    made_any = False
    os.makedirs("output", exist_ok=True)

    if args.schools:
        made_any = True
        # https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dschool indicates
        # primary and secondary schools
        generatePolygonLayer(args.osm_input, "amenity", "school", "schools")

    if args.hospitals:
        made_any = True
        # Note https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dhospital doesn't
        # cover all types of medical facility
        generatePolygonLayer(args.osm_input, "amenity", "hospital", "hospitals")

    if args.mrn:
        made_any = True
        makeMRN()

    if args.parliamentary_constituencies:
        made_any = True
        makeParliamentaryConstituencies()

    if args.wards:
        made_any = True
        makeWards(args.wards)

    if args.combined_authorities:
        made_any = True
        makeCombinedAuthorities()

    if args.local_authority_districts:
        made_any = True
        makeLocalAuthorityDistricts()

    if args.census_output_areas:
        made_any = True
        makeCensusOutputAreas(args.census_output_areas)

    if args.railway_stations:
        made_any = True
        makeRailwayStations(args.osm_input)

    if args.sports_spaces:
        made_any = True
        generatePolygonLayer(
            args.osm_input, "leisure", "pitch,sports_centre", "sports_spaces"
        )

    if not made_any:
        print(
            "Didn't create anything. Call with --help to see possible layers that can be created"
        )


# Extract `{tagPartOne}={tagPartTwo}` polygons from OSM, and only keep a name attribute.
def generatePolygonLayer(osm_input, tagPartOne, tagPartTwo, filename):
    if not osm_input:
        raise Exception("You must specify --osm_input")

    tmp = f"tmp_{filename}"
    ensureEmptyTempDirectoryExists(tmp)

    # First extract a .osm.pbf with all amenity={name} features
    # TODO Do we need nwr? We don't want points further on
    run(
        [
            "osmium",
            "tags-filter",
            osm_input,
            f"nwr/{tagPartOne}={tagPartTwo}",
            "-o",
            f"{tmp}/extract.osm.pbf",
        ]
    )

    # Transform osm.pbf to GeoJSON, only keeping polygons. (Everything will be expressed as a MultiPolygon)
    run(
        [
            "osmium",
            "export",
            f"{tmp}/extract.osm.pbf",
            "--geometry-type=polygon",
            "-o",
            f"{tmp}/extract.geojson",
        ]
    )

    removeNonNameProperties(f"{tmp}/extract.geojson")

    # Convert to pmtiles
    run(
        [
            "tippecanoe",
            f"{tmp}/extract.geojson",
            "--generate-ids",
            "-o",
            f"output/{filename}.pmtiles",
        ]
    )


def makeRailwayStations(
    osm_input,
):
    if not osm_input:
        raise Exception("You must specify --osm_input")

    filename = "railway_stations"
    tmp = f"tmp_{filename}"
    ensureEmptyTempDirectoryExists(tmp)
    osmFilePath = f"{tmp}/extract.osm.pbf"
    # First extract a .osm.pbf with all {tag_part_one}={tag_part_two} features
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
    generateGeojsonFromOSMFile(osmFilePath, outputFilepath)

    cleanUpGeojson(outputFilepath, ["name"], True)


def makeMRN():
    tmp = "tmp_mrn"
    ensureEmptyTempDirectoryExists(tmp)

    # Get the shapefile
    run(
        [
            "wget",
            "https://maps.dft.gov.uk/major-road-network-shapefile/Major_Road_Network_2018_Open_Roads.zip",
            "-O",
            f"{tmp}/Major_Road_Network_2018_Open_Roads.zip",
        ]
    )
    run(["unzip", f"{tmp}/Major_Road_Network_2018_Open_Roads.zip", "-d", tmp])

    # Convert to GeoJSON, projecting to WGS84
    run(
        [
            "ogr2ogr",
            "-f",
            "GeoJSON",
            f"{tmp}/mrn.geojson",
            "-t_srs",
            "EPSG:4326",
            f"{tmp}/Major_Road_Network_2018_Open_Roads.shp",
        ]
    )

    # Clean up the file
    path = f"{tmp}/mrn.geojson"
    print(f"Cleaning up {path}")
    gj = {}
    with open(path) as f:
        gj = json.load(f)
        # Remove unnecessary attributes
        del gj["name"]
        del gj["crs"]
        for feature in gj["features"]:
            # Remove all properties except for "name1", and rename it
            props = {}
            name = feature["properties"].get("name1")
            if name:
                props["name"] = name
            feature["properties"] = props

            feature["geometry"]["coordinates"] = trim_precision(
                feature["geometry"]["coordinates"]
            )
    with open(path, "w") as f:
        f.write(json.dumps(gj))

    # Convert to pmtiles
    run(["tippecanoe", path, "--generate-ids", "-o", "output/mrn.pmtiles"])


def makeParliamentaryConstituencies():
    tmp = "tmp_parliamentary_constituencies"
    ensureEmptyTempDirectoryExists(tmp)

    # Get the geopackage
    run(
        [
            "wget",
            # From https://osdatahub.os.uk/downloads/open/BoundaryLine
            "https://api.os.uk/downloads/v1/products/BoundaryLine/downloads?area=GB&format=GeoPackage&redirect",
            "-O",
            f"{tmp}/boundary_lines.zip",
        ]
    )
    run(["unzip", f"{tmp}/boundary_lines.zip", "-d", tmp])

    # Convert to GeoJSON, projecting to WGS84. Only grab one layer.
    run(
        [
            "ogr2ogr",
            "-f",
            "GeoJSON",
            f"{tmp}/parliamentary_constituencies.geojson",
            "-t_srs",
            "EPSG:4326",
            f"{tmp}/Data/bdline_gb.gpkg",
            "-sql",
            # Just get a few fields from one layer, and filter for England
            "SELECT Name, Census_Code, geometry FROM westminster_const WHERE Census_Code LIKE 'E%'",
        ]
    )

    # Convert to pmtiles
    run(
        [
            "tippecanoe",
            f"{tmp}/parliamentary_constituencies.geojson",
            "--generate-ids",
            "-o",
            "output/parliamentary_constituencies.pmtiles",
        ]
    )


# You have to manually download the GeoJSON file from https://geoportal.statistics.gov.uk/datasets/ons::wards-may-2023-boundaries-uk-bgc/explore and pass in the path here (until we can automate this)
def makeWards(path):
    tmp = "tmp_wards"
    ensureEmptyTempDirectoryExists(tmp)

    # Clean up the file
    print(f"Cleaning up {path}")
    gj = {}
    with open(path) as f:
        gj = json.load(f)
        # Remove unnecessary attributes
        del gj["name"]
        del gj["crs"]

        # Only keep England
        gj["features"] = list(
            filter(lambda f: f["properties"]["WD23CD"][0] == "E", gj["features"])
        )

        for feature in gj["features"]:
            # Remove most properties, and rename a few
            props = {}
            props["WD23CD"] = feature["properties"]["WD23CD"]
            props["name"] = feature["properties"]["WD23NM"]
            feature["properties"] = props

            feature["geometry"]["coordinates"] = trim_precision(
                feature["geometry"]["coordinates"]
            )
    with open(f"{tmp}/wards.geojson", "w") as f:
        f.write(json.dumps(gj))

    # Convert to pmtiles
    run(
        [
            "tippecanoe",
            f"{tmp}/wards.geojson",
            "--generate-ids",
            "-o",
            f"output/wards.pmtiles",
        ]
    )


def makeCombinedAuthorities():
    tmp = "tmp_combined_authorities"
    ensureEmptyTempDirectoryExists(tmp)

    # Reproject to WGS84
    run(
        [
            "ogr2ogr",
            "-f",
            "GeoJSON",
            f"{tmp}/boundary.geojson",
            "-t_srs",
            "EPSG:4326",
            "input/Combined_Authorities_December_2022_EN_BUC_1154653457304546671.geojson",
        ]
    )

    # Clean up the file. Note the features already have IDs.
    print(f"Cleaning up {tmp}/boundary.geojson")
    gj = {}
    with open(f"{tmp}/boundary.geojson") as f:
        gj = json.load(f)
        # Remove unnecessary attributes
        del gj["name"]
        del gj["crs"]

        for feature in gj["features"]:
            # Remove most properties, and rename a few
            props = {}
            props["CAUTH22CD"] = feature["properties"]["CAUTH22CD"]
            props["name"] = feature["properties"]["CAUTH22NM"]
            feature["properties"] = props

            feature["geometry"]["coordinates"] = trim_precision(
                feature["geometry"]["coordinates"]
            )
    # The final file is tiny; don't bother with pmtiles
    with open("output/combined_authorities.geojson", "w") as f:
        f.write(json.dumps(gj))


def makeLocalAuthorityDistricts():
    tmp = "tmp_local_authority_districts"
    ensureEmptyTempDirectoryExists(tmp)

    # Reproject to WGS84
    run(
        [
            "ogr2ogr",
            "-f",
            "GeoJSON",
            f"{tmp}/boundary.geojson",
            "-t_srs",
            "EPSG:4326",
            "input/Local_Authority_Districts_May_2023_UK_BUC_V2_-7390714061867823479.geojson",
        ]
    )

    # Clean up the file. Note the features already have IDs.
    print(f"Cleaning up {tmp}/boundary.geojson")
    gj = {}
    with open(f"{tmp}/boundary.geojson") as f:
        gj = json.load(f)
        # Remove unnecessary attributes
        del gj["name"]
        del gj["crs"]

        # Only keep England
        gj["features"] = list(
            filter(lambda f: f["properties"]["LAD23CD"][0] == "E", gj["features"])
        )

        for feature in gj["features"]:
            # Remove most properties, and rename a few
            props = {}
            props["LAD23CD"] = feature["properties"]["LAD23CD"]
            props["name"] = feature["properties"]["LAD23NM"]
            feature["properties"] = props

            feature["geometry"]["coordinates"] = trim_precision(
                feature["geometry"]["coordinates"]
            )
    # The final file is tiny; don't bother with pmtiles
    with open("output/local_authority_districts.geojson", "w") as f:
        f.write(json.dumps(gj))


# You have to manually download the GeoJSON file from https://geoportal.statistics.gov.uk/datasets/ons::output-areas-2021-boundaries-ew-bgc/explore and pass in the path here (until we can automate this)
def makeCensusOutputAreas(raw_boundaries_path):
    tmp = "tmp_census_output_areas"
    ensureEmptyTempDirectoryExists(tmp)

    # Build up a dictionary from OA code to properties we want
    oa_to_data = {}

    # Grab car availability data
    run(
        [
            "wget",
            "https://www.nomisweb.co.uk/output/census/2021/census2021-ts045.zip",
            "-O",
            f"{tmp}/census2021-ts045.zip",
        ]
    )
    # Only get one file from the .zip
    run(["unzip", f"{tmp}/census2021-ts045.zip", "census2021-ts045-oa.csv", "-d", tmp])
    with open(f"{tmp}/census2021-ts045-oa.csv") as f:
        for row in csv.DictReader(f):
            oa_to_data[row["geography code"]] = summarizeCarAvailability(row)

    # Grab population density
    run(
        [
            "wget",
            "https://www.nomisweb.co.uk/output/census/2021/census2021-ts006.zip",
            "-O",
            f"{tmp}/census2021-ts006.zip",
        ]
    )
    run(["unzip", f"{tmp}/census2021-ts006.zip", "census2021-ts006-oa.csv", "-d", tmp])
    with open(f"{tmp}/census2021-ts006-oa.csv") as f:
        for row in csv.DictReader(f):
            key = row["geography code"]
            # The set of OAs in both datasets match. Let a KeyError happen if not.
            oa_to_data[key]["population_density"] = round(
                float(
                    row[
                        "Population Density: Persons per square kilometre; measures: Value"
                    ]
                )
            )

    # Now work on the GeoJSON boundaries. First reproject to WGS84
    path = f"{tmp}/census_output_areas.geojson"
    run(
        [
            "ogr2ogr",
            "-f",
            "GeoJSON",
            path,
            "-t_srs",
            "EPSG:4326",
            raw_boundaries_path,
        ]
    )

    # Clean up the GeoJSON file, and add in the per-OA data above
    print(f"Cleaning up {path}")
    gj = {}
    with open(path) as f:
        gj = json.load(f)
        # Remove unnecessary attributes
        del gj["name"]
        del gj["crs"]
        for feature in gj["features"]:
            key = feature["properties"]["OA21CD"]
            props = oa_to_data[key]
            props["OA21CD"] = key
            feature["properties"] = props

            feature["geometry"]["coordinates"] = trim_precision(
                feature["geometry"]["coordinates"]
            )
    with open(path, "w") as f:
        f.write(json.dumps(gj))

    # Convert to pmtiles
    run(
        [
            "tippecanoe",
            path,
            "--generate-ids",
            "-o",
            "output/census_output_areas.pmtiles",
        ]
    )


def summarizeCarAvailability(row):
    # hh = household
    hh_with_0 = int(row["Number of cars or vans: No cars or vans in household"])
    hh_with_1 = int(row["Number of cars or vans: 1 car or van in household"])
    hh_with_2 = int(row["Number of cars or vans: 2 cars or vans in household"])
    hh_with_more = int(
        row["Number of cars or vans: 3 or more cars or vans in household"]
    )
    # There's also a column for this
    total_households = hh_with_0 + hh_with_1 + hh_with_2 + hh_with_more
    # Assume 3 cars for "3 or more"
    total_cars = hh_with_1 + 2 * hh_with_2 + 3 * hh_with_more

    return {
        # 0-100, rounded for space efficiency
        "percent_households_with_car": 100 - round(hh_with_0 / total_households * 100),
        # Round to 1 decimal place
        "average_cars_per_household": round(total_cars / total_households, 1),
    }


def generateGeojsonFromOSMFile(osmFilePath, outputFilepath):
    run(
        [
            "osmium",
            "export",
            osmFilePath,
            "-o",
            outputFilepath,
        ]
    )


def ensureEmptyTempDirectoryExists(directoryName):
    if os.path.isdir(directoryName):
        run(["rm", "-r", directoryName])
    os.makedirs(directoryName, exist_ok=True)


def run(args):
    print(">", " ".join(args))
    subprocess.run(args, check=True)


# For each GeoJSON feature, keep only the name attribute. Overwrites the given file.
def removeNonNameProperties(path):
    cleanUpGeojson(path, ["name"])

def cleanUpGeojson(path, propertiesToKeep, addIds=False):
    print(f"Cleaning up {path}")
    gj = {}
    with open(path) as f:
        gj = json.load(f)

        counter = 1
        for feature in gj["features"]:
            # Only keep one property
            keptProperties = {}
            for property in propertiesToKeep:
                valueToKeep =  feature["properties"].get(property) 
                if(valueToKeep):
                    keptProperties[property] = valueToKeep
            feature["properties"] = keptProperties

            feature["geometry"]["coordinates"] = trim_precision(
                feature["geometry"]["coordinates"]
            )

            # The frontend needs IDs for hovering
            if(addIds):
                feature["id"] = counter
                counter += 1
    with open(path, "w") as f:
        f.write(json.dumps(gj))

# Round coordinates to 6 decimal places. Takes feature.geometry.coordinates,
# handling any type.
def trim_precision(data):
    if isinstance(data, list):
        return [trim_precision(x) for x in data]
    elif isinstance(data, float):
        return round(data, 6)
    else:
        raise Exception(f"Unexpected data within coordinates: {data}")


if __name__ == "__main__":
    main()
