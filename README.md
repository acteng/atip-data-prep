# A/B Street to ATIP import

This repo has some scripts to import data required by ATIP.

- `authorities.geojson` has a Polygon boundary for every Local Authority District and Transport Authority
  - The data comes from https://github.com/acteng/boundaries, and then
    `fix_boundaries` is used to turn MultiPolygons into a single Polygon with
    convex hull.
- Ignore the `experimental` directory; nothing is actively used there

## Splitting huge OSM files

The pipelines in this repo need two files as input: an OSM XML file and a
GeoJSON file with a single polygon, representing the area clipped in that OSM
file. For ATIP, we want to repeat this for every LAD and TA in the UK.

To run this:

1.  Make sure you have about 35GB of disk free
2.  Install [osmium](https://osmcode.org/osmium-tool)
3.  Manually adjust scripts if needed, based on your own computer's resources
4.  Run `./split_uk_osm.sh`

This will download England-wide osm.pbf from Geofabrik, produce a bunch of
GeoJSON files and Osmium extract configs (`geojson_to_osmium_extracts.py`), and
run osmium in batches. Each osmium pass through the gigantic pbf file works on
some number of output files, based on the batch size. 1 area at a time is slow,
but too many at once will consume lots of RAM.

## Route snapper

ATIP's route snapper tool loads a binary file per authority area.

To regenerate them:

1.  Install [pueue](https://github.com/Nukesor/pueue)
2.  Set up the submodules in this repo: `git submodule init && git submodule update`
3.  Complete the section above to split OSM files
4.  Make sure the pueue daemon is started, and tasks cleared out. (`pueued -d; pueue status; pueue clean`
5.  Run `./build_route_snappers.sh`
6.  Wait for all pueue commands to succeed (`pueue status`)
7.  Manually upload to S3, following instructions in that script

## Route info

ATIP also loads a binary A/B Street map model file per area, using it to answer things about routes.

To regenerate them, follow the same procedure as above, running
`./build_route_info.sh` instead of `build_route_snappers.sh`. If you have
trouble building the A/B Street importer, see [these
instructions](https://a-b-street.github.io/docs/tech/dev/index.html).

IMPORTANT! The abstreet submodule must be kept in sync with the git version
used by ATIP's [route info
crate](https://github.com/acteng/atip/tree/map_model/route_info). Otherwise,
the binary file format may be incompatible.
