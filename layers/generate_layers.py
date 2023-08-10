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
    parser.add_argument("--local_planning_authorities", action="store_true")
    parser.add_argument(
        "--census_output_areas",
        help="Path to the manually downloaded Output_Areas_2021_EW_BGC_V2_-3080813486471056666.geojson",
        type=str,
    )
    parser.add_argument("--bus_routes", action="store_true")
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
        generatePolygonLayer(args.osm_input, "amenity=school", "schools")

    if args.hospitals:
        made_any = True
        # Note https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dhospital doesn't
        # cover all types of medical facility
        generatePolygonLayer(args.osm_input, "amenity=hospital", "hospitals")

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

    if args.local_planning_authorities:
        made_any = True
        makeLocalPlanningAuthorities()

    if args.census_output_areas:
        made_any = True
        makeCensusOutputAreas(args.census_output_areas)

    if args.railway_stations:
        made_any = True
        makeRailwayStations(args.osm_input)

    if args.sports_spaces:
        made_any = True
        generatePolygonLayer(
            args.osm_input, "leisure=pitch,sports_centre", "sports_spaces"
        )

    if args.bus_routes:
        made_any = True
        makeBusRoutes(args.osm_input)

    if not made_any:
        print(
            "Didn't create anything. Call with --help to see possible layers that can be created"
        )


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

            feature["geometry"]["coordinates"] = trimPrecision(
                feature["geometry"]["coordinates"]
            )
    with open(path, "w") as f:
        f.write(json.dumps(gj))

    convertGeoJsonToPmtiles(path, "output/mrn.pmtiles")


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

    convertGeoJsonToPmtiles(
        f"{tmp}/parliamentary_constituencies.geojson",
        "output/parliamentary_constituencies.pmtiles",
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

            feature["geometry"]["coordinates"] = trimPrecision(
                feature["geometry"]["coordinates"]
            )
    with open(f"{tmp}/wards.geojson", "w") as f:
        f.write(json.dumps(gj))

    convertGeoJsonToPmtiles(f"{tmp}/wards.geojson", "output/wards.pmtiles")


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
            # Manually downloaded and stored in git
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

            feature["geometry"]["coordinates"] = trimPrecision(
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
            # Manually downloaded and stored in git
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

            feature["geometry"]["coordinates"] = trimPrecision(
                feature["geometry"]["coordinates"]
            )
    # The final file is tiny; don't bother with pmtiles
    with open("output/local_authority_districts.geojson", "w") as f:
        f.write(json.dumps(gj))


def makeLocalPlanningAuthorities():
    tmp = "tmp_local_planning_authorities"
    os.makedirs(tmp, exist_ok=True)

    # Alternatively, the original source here seems to be
    # https://geoportal.statistics.gov.uk/datasets/ons::local-planning-authorities-april-2022-uk-bgc-3/explore
    path = f"{tmp}/local_planning_authorities.geojson"
    run(
        [
            "wget",
            "https://files.planning.data.gov.uk/dataset/local-planning-authority.geojson",
            "-O",
            path,
        ]
    )

    # Clean up the file
    print(f"Cleaning up {path}")
    gj = {}
    with open(path) as f:
        gj = json.load(f)
        # Remove unnecessary attributes
        del gj["name"]

        for feature in gj["features"]:
            # Remove most properties, and rename a few
            props = {}
            props["LPA22CD"] = feature["properties"]["reference"]
            props["name"] = feature["properties"]["name"]
            feature["properties"] = props
            # The precision is already trimmed
    with open(path, "w") as f:
        f.write(json.dumps(gj))

    convertGeoJsonToPmtiles(path, "output/local_planning_authorities.pmtiles")


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

            feature["geometry"]["coordinates"] = trimPrecision(
                feature["geometry"]["coordinates"]
            )
    with open(path, "w") as f:
        f.write(json.dumps(gj))

    convertGeoJsonToPmtiles(path, "output/census_output_areas.pmtiles")


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

    # We're not handling highway=busway or other cases for service roads
    # designed exclusively for buses, because they're not intended for cyclists
    # or any other users.

    return False


def convertPbfToGeoJson(pbfPath, geojsonPath, geometryType):
    run(
        [
            "osmium",
            "export",
            osmFilePath,
            f"--geometry-type={geometryType}",
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


# Adds numeric IDs to every feature, trims coordinate precision, and only keeps
# the specified properties. Overwrites the file.
def cleanUpGeojson(path, propertiesToKeep):
    print(f"Cleaning up {path}")
    gj = {}
    with open(path) as f:
        gj = json.load(f)

        counter = 1
        for feature in gj["features"]:
            keptProperties = {}
            for property in propertiesToKeep:
                valueToKeep = feature["properties"].get(property)
                if valueToKeep:
                    keptProperties[property] = valueToKeep
            feature["properties"] = keptProperties

            feature["geometry"]["coordinates"] = trimPrecision(
                feature["geometry"]["coordinates"]
            )

            # The frontend needs IDs for hovering
            feature["id"] = counter
            counter += 1
    with open(path, "w") as f:
        f.write(json.dumps(gj))


# Note the layer name is based on the input filename. This always generates
# numeric feature IDs.
def convertGeoJsonToPmtiles(geojsonPath, pmtilesPath):
    run(["tippecanoe", geojsonPath, "--generate-ids", "-o", pmtilesPath])


# Round coordinates to 6 decimal places. Takes feature.geometry.coordinates,
# handling any type.
def trimPrecision(data):
    if isinstance(data, list):
        return [trimPrecision(x) for x in data]
    elif isinstance(data, float):
        return round(data, 6)
    else:
        raise Exception(f"Unexpected data within coordinates: {data}")


if __name__ == "__main__":
    main()
