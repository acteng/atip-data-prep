import csv
from utils import *


def makeDftVehicleCounts():
    tmp = "tmp_vehicle_counts"
    ensureEmptyTempDirectoryExists(tmp)

    run(
        [
            "wget",
            # From https://roadtraffic.dft.gov.uk/downloads
            "https://storage.googleapis.com/dft-statistics/road-traffic/downloads/data-gov-uk/dft_traffic_counts_aadf.zip",
            "-O",
            f"{tmp}/dft_traffic_counts_aadf.zip",
        ]
    )
    run(["unzip", f"{tmp}/dft_traffic_counts_aadf.zip", "-d", tmp])

    gj = {
        "type": "FeatureCollection",
        "features": [],
    }

    with open(f"{tmp}/dft_traffic_counts_aadf.csv") as f:
        for row in csv.DictReader(f):
            # Only keep the latest year and England
            if row["Year"] != "2022" or row["Region_ons_code"][0] != "E":
                continue

            gj["features"].append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            float(row["Longitude"]),
                            float(row["Latitude"]),
                        ],
                    },
                    "properties": {
                        "count_point": row["Count_point_id"],
                        "location": f"{row['Road_name']} from {row['Start_junction_road_name']} to {row['End_junction_road_name']}",
                        "method": row["Estimation_method_detailed"],
                        "motor_vehicles_2022": int(row["All_motor_vehicles"]),
                        "pedal_cycles_2022": int(row["Pedal_cycles"]),
                    },
                }
            )

    with open(f"{tmp}/vehicle_counts.geojson", "w") as f:
        f.write(json.dumps(gj))
    convertGeoJsonToPmtiles(
        f"{tmp}/vehicle_counts.geojson", "output/vehicle_counts.pmtiles", autoZoom=True
    )
