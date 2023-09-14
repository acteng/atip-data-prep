from utils import *


def makePct():
    tmp = "tmp_pct"
    ensureEmptyTempDirectoryExists(tmp)

    run(
        [
            "wget",
            "https://github.com/npct/pct-outputs-national/raw/master/commute/lsoa/rnet_all.geojson",
            "-O",
            f"{tmp}/commute.geojson",
        ]
    )

    run(
        [
            "wget",
            "https://github.com/npct/pct-outputs-national/raw/master/school/lsoa/rnet_all.geojson",
            "-O",
            f"{tmp}/school.geojson",
        ]
    )

    # The two trip purposes are split into different files, and neither feature
    # ID nor the local_id property matches between them. So just output two
    # separate files.

    def fixProps(inputProps):
        return {
            "baseline": int(inputProps["bicycle"]),
            "gov_target": int(inputProps["govtarget_slc"]),
            "go_dutch": int(inputProps["dutch_slc"]),
        }

    cleanUpGeojson(f"{tmp}/commute.geojson", fixProps)
    convertGeoJsonToPmtiles(
        f"{tmp}/commute.geojson",
        f"output/pct_commute.pmtiles",
        args=["--drop-densest-as-needed"],
    )

    # The school network is missing counts on many features
    cleanUpGeojson(
        f"{tmp}/school.geojson",
        fixProps,
        filterFeatures=lambda f: f["properties"]["bicycle"] is not None,
    )
    convertGeoJsonToPmtiles(
        f"{tmp}/school.geojson",
        f"output/pct_school.pmtiles",
        args=["--drop-densest-as-needed"],
    )
