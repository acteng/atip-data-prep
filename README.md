# ATIP data prep

This repo has some scripts to import data required by ATIP.

- `authorities.geojson` has a Polygon boundary for every Local Authority District and Transport Authority
  - The data comes from https://github.com/acteng/boundaries, and then
    `fix_boundaries` is used to turn MultiPolygons into a single Polygon with
    convex hull.
- Ignore the `experimental` directory; nothing is actively used there

## Splitting huge OSM files

Some pipelines in this repo need two files as input: an OSM XML file and a
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

1.  Make sure you have about 25GB of disk free
2.  Install [pueue](https://github.com/Nukesor/pueue)
3.  Set up the submodules in this repo: `git submodule init && git submodule update`
4.  Complete the section above to split OSM files
5.  Make sure the pueue daemon is started, and tasks cleared out. (`pueued -d; pueue status; pueue clean`)
6.  Run `./build_route_snappers.sh`
7.  Wait for all pueue commands to succeed (`pueue status`)
8.  Manually upload to S3, following instructions in that script

To update to a newer commit in the [route-snapper
repo](https://github.com/dabreegster/route_snapper), run `git submodule update
--remote`.

## Route info

ATIP also loads a binary osm2streets file per area, using it to answer things
about routes.

To regenerate them, follow the same procedure as above, running
`./build_route_info.sh` instead of `build_route_snappers.sh`. You will need to
[install Rust](https://www.rust-lang.org/tools/install).

IMPORTANT! The `importer` crate's dependency on `osm2streets` must be kept in
sync with the git version used by ATIP's [route info
crate](https://github.com/acteng/atip/tree/map_model/route_info). Otherwise,
the binary file format may be incompatible. Use `cargo update -p osm2streets`.

## POIs (points of interest)

ATIP loads extra layers showing key destinations. These layers are
England-wide, rather than being split into a file per area, because they're
being used on the country-wide scheme browse page. Each layer is a single
[PMTiles](https://protomaps.com/docs/pmtiles/) file.

To run this:

1.  Get `england-latest.osm.pbf` from Geofabrik. The `split_uk_osm.sh` script above does this.
2.  Install [osmium](https://osmcode.org/osmium-tool)
3.  Install [tippecanoe](https://github.com/felt/tippecanoe) for transforming GeoJSON to PMTiles
4.  Run `cd pois; generate_pois.py ../england-latest.osm.pbf`
5.  Pick an arbitrary version number, and upload the file: `aws s3 cp --dry schools.pmtiles s3://atip.uk/layers/v1/`

You can debug a PMTiles file using <https://protomaps.github.io/PMTiles>.

### One-time cloud setup for PMTiles

Currently we're using S3 and Cloudfront to host files generated by this repo.
As a one-time setup, the S3 CORS policy has to be edited per
<https://protomaps.com/docs/pmtiles/cloud-storage>.

Also the Cloudfront settings have to be modified on the appropriate distribution's "Behavior" page:

- Allow GET, HEAD, and OPTIONS methods
- Create a response headers policy
  - Configure CORS with default options
  - Add a custom ETag header with no value, and not overriding the origin
  - Set the distribution to use this policy
