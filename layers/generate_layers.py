#!/usr/bin/python3

import argparse
import csv

from utils import *
import census
import boundaries
import osm


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
    parser.add_argument("--cycle_parking", action="store_true")
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
        boundaries.makeWards(args.wards)

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


if __name__ == "__main__":
    main()
