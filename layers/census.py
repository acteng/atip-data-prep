import csv
from utils import *

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

    path = f"{tmp}/census_output_areas.geojson"
    reprojectToWgs84(raw_boundaries_path, path)

    def fixProps(inputProps):
        outputProps = {}
        key = inputProps["OA21CD"]
        outputProps.update(oa_to_data[key])
        outputProps["OA21CD"] = key
        return outputProps

    cleanUpGeojson(path, fixProps)

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


# You have to manually download the GeoJSON file from https://data-communities.opendata.arcgis.com/datasets/communities::indices-of-multiple-deprivation-imd-2019-1/explore and pass in the path here (until we can automate this)
def makeIMD(path):
    def fixProps(inputProps):
        # See https://data-communities.opendata.arcgis.com/datasets/communities::indices-of-multiple-deprivation-imd-2019-1/about
        outputProps = {
            "LSOA11CD": inputProps["lsoa11cd"],
            "score": round(inputProps["IMDScore"], 1),
            "rank": inputProps["IMDRank0"],
            "decile": inputProps["IMDDec0"],
        }
        return outputProps

    # Note the 2019 IMD data uses 2011 LSOAs. We don't have any other census
    # data against 2011 LSOAs, so we're not combining it with anything else.
    cleanUpGeojson(path, fixProps)
    convertGeoJsonToPmtiles(path, f"output/imd.pmtiles")
