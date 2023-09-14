#!/usr/bin/python3

import argparse

from utils import *
import census
import boundaries
import cycle_paths
import osm
import traffic


def main():
    parser = argparse.ArgumentParser()
    # Possible outputs to generate
    parser.add_argument("--schools", action="store_true")
    parser.add_argument("--hospitals", action="store_true")
    parser.add_argument("--mrn", action="store_true")
    parser.add_argument("--parliamentary_constituencies", action="store_true")
    parser.add_argument("--railway_stations", action="store_true")
    parser.add_argument("--crossings", action="store_true")
    parser.add_argument("--sports_spaces", action="store_true")
    parser.add_argument("--wards", action="store_true")
    parser.add_argument("--combined_authorities", action="store_true")
    parser.add_argument("--local_authority_districts", action="store_true")
    parser.add_argument("--local_planning_authorities", action="store_true")
    parser.add_argument(
        "--census_output_areas",
        help="Path to the manually downloaded Output_Areas_2021_EW_BGC_V2_-3080813486471056666.geojson",
        type=str,
    )
    parser.add_argument("--bus_routes", action="store_true")
    parser.add_argument("--cycle_parking", action="store_true")
    parser.add_argument(
        "--imd",
        help="Path to the manually downloaded Indices_of_Multiple_Deprivation_(IMD)_2019.geojson",
        type=str,
    )
    parser.add_argument("--cycle_paths", action="store_true")
    parser.add_argument("--vehicle_counts", action="store_true")
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
        osm.generatePolygonLayer(args.osm_input, "amenity=school", "schools")

    if args.hospitals:
        made_any = True
        # Note https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dhospital doesn't
        # cover all types of medical facility
        osm.generatePolygonLayer(args.osm_input, "amenity=hospital", "hospitals")

    if args.mrn:
        made_any = True
        makeMRN()

    if args.parliamentary_constituencies:
        made_any = True
        boundaries.makeParliamentaryConstituencies()

    if args.wards:
        made_any = True
        boundaries.makeWards()

    if args.combined_authorities:
        made_any = True
        boundaries.makeCombinedAuthorities()

    if args.local_authority_districts:
        made_any = True
        boundaries.makeLocalAuthorityDistricts()

    if args.local_planning_authorities:
        made_any = True
        boundaries.makeLocalPlanningAuthorities()

    if args.census_output_areas:
        made_any = True
        census.makeCensusOutputAreas(args.census_output_areas)

    if args.railway_stations:
        made_any = True
        osm.makeRailwayStations(args.osm_input)

    if args.sports_spaces:
        made_any = True
        osm.generatePolygonLayer(
            args.osm_input, "leisure=pitch,sports_centre", "sports_spaces"
        )

    if args.bus_routes:
        made_any = True
        osm.makeBusRoutes(args.osm_input)

    if args.cycle_parking:
        made_any = True
        osm.makeCycleParking(args.osm_input)

    if args.crossings:
        made_any = True
        osm.makeCrossings(args.osm_input)

    if args.imd:
        made_any = True
        census.makeIMD(args.imd)

    if args.cycle_paths:
        made_any = True
        cycle_paths.makeCyclePaths(args.osm_input)

    if args.vehicle_counts:
        made_any = True
        traffic.makeDftVehicleCounts()

    if not made_any:
        print(
            "Didn't create anything. Call with --help to see possible layers that can be created"
        )


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

    reprojectToWgs84(
        f"{tmp}/Major_Road_Network_2018_Open_Roads.shp", f"{tmp}/mrn.geojson"
    )

    def fixProps(inputProps):
        outputProps = {}
        name = feature["properties"].get("name1")
        if name:
            outputProps["name"] = name
        return outputProps

    cleanUpGeojson(f"{tmp}/mrn.geojson", fixProps)

    convertGeoJsonToPmtiles(f"{tmp}/mrn.geojson", "output/mrn.pmtiles")


if __name__ == "__main__":
    main()
