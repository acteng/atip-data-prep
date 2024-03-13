import csv
from collections import defaultdict
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

    # Group per-year rows by count point
    rows_per_count_point = defaultdict(list)
    with open(f"{tmp}/dft_traffic_counts_aadf.csv") as f:
        for row in csv.DictReader(f):
            # Only keep England
            if row["Region_ons_code"][0] != "E":
                continue
            rows_per_count_point[row["Count_point_id"]].append(row)

    gj = {
        "type": "FeatureCollection",
        "features": [],
    }
    for (count_point, rows) in rows_per_count_point.items():
        # Find the latest year per count point
        latest = max(rows, key=lambda row: int(row["Year"]))
        location = latest["Road_name"]
        if latest["Start_junction_road_name"]:
            location += f" from {latest['Start_junction_road_name']} to {latest['End_junction_road_name']}"

        gj["features"].append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(latest["Longitude"]),
                        float(latest["Latitude"]),
                    ],
                },
                "properties": {
                    "count_point": latest["Count_point_id"],
                    "location": location,
                    "method": latest["Estimation_method_detailed"],
                    "motor_vehicles": int(latest["All_motor_vehicles"]),
                    "pedal_cycles": int(latest["Pedal_cycles"]),
                    "year": int(latest["Year"]),
                },
            }
        )

    with open(f"{tmp}/vehicle_counts.geojson", "w") as f:
        f.write(json.dumps(gj))
    convertGeoJsonToPmtiles(
        f"{tmp}/vehicle_counts.geojson", "output/vehicle_counts.pmtiles", autoZoom=True
    )
