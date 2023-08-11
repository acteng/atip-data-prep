from utils import *


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
