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


def makeWards():
    tmp = "tmp_wards"
    ensureEmptyTempDirectoryExists(tmp)

    run(
        [
            "wget",
            # From https://geoportal.statistics.gov.uk/datasets/ons::wards-may-2023-boundaries-uk-bgc/explore
            "https://opendata.arcgis.com/api/v3/datasets/67c88ea8027244e3b2313c69e3fad503_0/downloads/data?format=geojson&spatialRefId=4326&where=1%3D1",
            "-O",
            f"{tmp}/wards.geojson",
        ]
    )

    def fixProps(inputProps):
        return {
            "WD23CD": inputProps["WD23CD"],
            "name": inputProps["WD23NM"],
        }

    cleanUpGeojson(
        f"{tmp}/wards.geojson",
        fixProps,
        # Only keep England
        filterFeatures=lambda f: f["properties"]["WD23CD"][0] == "E",
    )

    convertGeoJsonToPmtiles(f"{tmp}/wards.geojson", "output/wards.pmtiles")


def makeCombinedAuthorities():
    reprojectToWgs84(
        # Manually downloaded and stored in git
        "input/Combined_Authorities_December_2022_EN_BUC_1154653457304546671.geojson",
        "output/combined_authorities.geojson",
    )

    def fixProps(inputProps):
        return {
            "CAUTH22CD": inputProps["CAUTH22CD"],
            "name": inputProps["CAUTH22NM"],
        }

    # The final file is tiny; don't bother with pmtiles
    cleanUpGeojson("output/combined_authorities.geojson", fixProps)


def makeLocalAuthorityDistricts():
    tmp = "tmp_local_authority_districts"
    ensureEmptyTempDirectoryExists(tmp)

    reprojectToWgs84(
        # Manually downloaded and stored in git
        "input/Local_Authority_Districts_May_2023_UK_BUC_V2_-7390714061867823479.geojson",
        "output/local_authority_districts.geojson",
    )

    def fixProps(inputProps):
        return {
            "LAD23CD": inputProps["LAD23CD"],
            "name": inputProps["LAD23NM"],
        }

    # The final file is tiny; don't bother with pmtiles
    cleanUpGeojson(
        "output/local_authority_districts.geojson",
        fixProps,
        # Only keep England
        filterFeatures=lambda f: f["properties"]["LAD23CD"][0] == "E",
    )

def makeLocalAuthorityDistrictsForSketcher():
    outputFilePath = "output/local_authority_districts_reprojected.geojson"

    reprojectToWgs84(
        # Manually acquired output from acteng/boundaries
        "input/lads.geojson",
        outputFilePath,
    )

    def fixProps(inputProps):
        return {
            "name": inputProps["LAD23NM"],
            "level": "LAD",
        }

    cleanUpGeojson(
        outputFilePath,
        fixProps,
        # Only keep England
        filterFeatures=lambda f: f["properties"]["LAD23CD"][0] == "E",
    )
    removePolygonHoles(outputFilePath)

def makeTransportAuthoritiesForSketcher():
    outputFilePath = "output/transport_authorities_reprojected.geojson"

    reprojectToWgs84(
        # Manually acquired output from acteng/boundaries
        "input/transport_authorities.geojson",
        outputFilePath,
    )

    def fixProps(inputProps):
        return {
            "name": inputProps["atf4_authority_name"],
            "level": "TA",
        }

    cleanUpGeojson(
        outputFilePath,
        fixProps,
    )
    removePolygonHoles(outputFilePath)

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

    def fixProps(inputProps):
        return {
            "LPA22CD": inputProps["reference"],
            "name": inputProps["name"],
        }

    cleanUpGeojson(path, fixProps)

    convertGeoJsonToPmtiles(path, "output/local_planning_authorities.pmtiles")
