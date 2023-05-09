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

1.  Install [osmium](https://osmcode.org/osmium-tool)
2.  Manually adjust scripts if needed, based on your own computer's resources
3.  Run `./split_uk_osm.sh`

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
4.  Run `./build_route_snappers.sh`
5.  Manually upload to S3, following instructions in that script
