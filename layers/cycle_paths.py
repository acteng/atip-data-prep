from utils import *


def makeCyclePaths(osm_input):
    if not osm_input:
        raise Exception("You must specify --osm_input")

    filename = "cycle_paths"
    tmp = f"tmp_{filename}"
    ensureEmptyTempDirectoryExists(tmp)

    run(
        [
            "osmium",
            "tags-filter",
            osm_input,
            "w/highway",
            "-o",
            f"{tmp}/cycle_paths.osm.pbf",
        ]
    )
    gjPath = f"{tmp}/cycle_paths.geojson"
    convertPbfToGeoJson(
        f"{tmp}/cycle_paths.osm.pbf", gjPath, "linestring", includeOsmID=True
    )

    cleanUpGeojson(
        gjPath, getProps, filterFeatures=lambda f: getProps(f["properties"]) != None
    )

    convertGeoJsonToPmtiles(f"{tmp}/cycle_paths.geojson", "output/cycle_paths.pmtiles")


# If this has some kind of cycle-path, returns a dictionary with:
#
# - kind = track | lane | shared_use_segregated | shared_use_unsegregated
# - osm_id
# - direction = one-way | two-way | unknown
#   (For cyclist traffic; unrelated to whether the path is a contraflow on a one-way street)
# - width = number in meters | unknown
#
# If there's no cycle path, returns None
def getProps(props):
    if props.get("highway") == "cycleway":
        kind = "track"
        # Is it shared-use? Note "foot" may be missing (https://www.openstreetmap.org/way/849651126)
        if props.get("foot") in ["yes", "designated"] or props.get("segregated"):
            kind = getSharedUseKind(props)

        return {
            "kind": kind,
            "osm_id": props["@id"],
            "width": getSeparateWayWidth(props),
            "direction": getSeparateWayDirection(props),
        }
    elif hasLane(props):
        return {
            "kind": "lane",
            "osm_id": props["@id"],
            "width": getLaneWidth(props),
            "direction": getLaneDirection(props),
        }
    elif props["highway"] in ["footway", "pedestrian", "path", "track"]:
        if props.get("bicycle") not in ["yes", "designated"]:
            return None

        return {
            "kind": getSharedUseKind(props),
            "osm_id": props["@id"],
            "width": getSeparateWayWidth(props),
            "direction": getSeparateWayDirection(props),
        }
    else:
        return None


def getSeparateWayWidth(props):
    # TODO Handle suffixes / units
    if props.get("width"):
        return props["width"]
    if props.get("est_width"):
        return props["est_width"]
    return "unknown"


def getSeparateWayDirection(props):
    oneway = props.get("oneway")
    if oneway == "yes":
        return "one-way"
    elif oneway == "no":
        return "two-way"
    else:
        return "unknown"


def valueIndicatesLane(value):
    return value and value not in ["no", "separate", "share_busway"]


def hasLane(props):
    # TODO Handle bicycle:lanes
    for suffix in ["", ":left", ":right", ":both"]:
        if valueIndicatesLane(props.get("cycleway" + suffix)):
            return True
    return False


# If there are two lanes, the result could capture one or both of the lanes
def getLaneWidth(props):
    for suffix in ["", ":left", ":right", ":both"]:
        for width in [":width", ":est_width"]:
            value = props.get("cycleway" + suffix + width)
            if value:
                return value
    return "unknown"


def getLaneDirection(props):
    if valueIndicatesLane(props.get("cycleway:both")):
        return "two-way"
    if valueIndicatesLane(props.get("cycleway:left")) and valueIndicatesLane(
        props.get("cycleway:right")
    ):
        return "two-way"
    if props.get("oneway:bicycle") == "no":
        # TODO On one-way roads, this might just mean cyclists can travel both
        # directions, but there's only a dedicated lane in one
        return "two-way"
    if (
        props.get("cycleway:left:oneway") == "no"
        or props.get("cycleway:right:oneway") == "no"
    ):
        return "two-way"

    # TODO opposite_track
    # TODO cycleway=* + oneway=yes
    # TODO bicycle:lanes
    return "unknown"


def getSharedUseKind(props):
    segregated = props.get("segregated")
    if segregated == "yes":
        return "shared_use_segregated"
    elif segregated == "no":
        return "shared_use_unsegregated"
    else:
        # Pessimistically assume unsegregated if unknown
        return "shared_use_unsegregated"
