# ATIP data prep

This repo has some scripts to import data required by ATIP.

The sections below describe different portions of the repo. Files/directories not covered below include:

- `authorities.geojson` has a Polygon boundary for every Local Authority District and Transport Authority
  - The data comes from https://github.com/acteng/boundaries, and then
    `fix_boundaries` is used to turn MultiPolygons into a single Polygon with
    convex hull.
- Ignore the `experimental` directory; nothing is actively used there

## Setup

To run all of the scripts in this repo, you'll need a number of dependencies.
Currently these are all run by Dustin on a local machine, with no
performance/scaling problems at all. We can bundle dependencies in Docker in
the future if needed.

- Standard Unix tools: `unzip`, `wget`, `python3` (without any dependencies yet)
- [Rust](https://www.rust-lang.org/tools/install)
- [osmium](https://osmcode.org/osmium-tool)
- [pueue](https://github.com/Nukesor/pueue)
- [tippecanoe](https://github.com/felt/tippecanoe)
- [GDAL](https://gdal.org/download.html)
- The [aws CLI](https://aws.amazon.com/cli/)
  - Currently only Dustin has permission to push to the S3 bucket. This will
    transition to GCS in the future.

## Splitting huge OSM files

Some pipelines in this repo need two files as input: an OSM XML file and a
GeoJSON file with a single polygon, representing the area clipped in that OSM
file. For ATIP, we want to repeat this for every LAD and TA in the UK.

To run this:

1.  Make sure you have about 35GB of disk free
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

1.  Make sure you have about 25GB of disk free
2.  Set up the submodules in this repo: `git submodule init && git submodule update`
3.  Complete the section above to split OSM files
4.  Make sure the pueue daemon is started, and tasks cleared out. (`pueued -d; pueue status; pueue clean`)
5.  Run `./build_route_snappers.sh`
6.  Wait for all pueue commands to succeed (`pueue status`)
7.  Manually upload to S3, following instructions in that script

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

## Extra contextual layers

ATIP can display extra contextual layers:

- POIs (points of interest) from OpenStreetMap, like schools and hospitals
- the [Major Road Network](https://www.data.gov.uk/dataset/95f58bfa-13d6-4657-9d6f-020589498cfd/major-road-network)
- Parliament constituency boundaries, from [OS Boundary-Line](https://www.ordnancesurvey.co.uk/products/boundary-line)
- Wards, from [OS and ONS](https://geoportal.statistics.gov.uk/datasets/ons::wards-may-2023-boundaries-uk-bgc/explore)
- Combined authorities from [OS and ONS](https://geoportal.statistics.gov.uk/datasets/ons::combined-authorities-december-2022-boundaries-en-buc/explore)
- Local authority districts from [OS and ONS](https://geoportal.statistics.gov.uk/datasets/ons::local-authority-districts-may-2023-boundaries-uk-buc/explore)
- Output-area level 2021 census data
	- Output area boundaries from [OS and ONS](https://geoportal.statistics.gov.uk/datasets/ons::output-areas-2021-boundaries-ew-bgc/explore)
	- Population density comes from [NOMIS TS006](https://www.nomisweb.co.uk/sources/census_2021_bulk)
	- Car/van availability comes from [NOMIS TS004](https://www.nomisweb.co.uk/output/census/2021/census2021-ts045.zip)

These layers are England-wide, rather than being split into a file per area,
because they're being used on the country-wide scheme browse page. Each layer
is a single GeoJSON file if it's small enough, or
[PMTiles](https://protomaps.com/docs/pmtiles/) for larger ones.

To run this:

1.  Get `england-latest.osm.pbf` from Geofabrik. The `split_uk_osm.sh` script above does this.
2.  Run `cd layers; ./generate_layers.py --osm_input=../england-latest.osm.pbf --schools --hospitals --mrn --parliamentary_constituencies --combined_authorities --local_authority_districts`
3.  Pick an arbitrary version number, and upload the files: `for x in output/*; do aws s3 cp --dry $x s3://atip.uk/layers/v1/; done`

If you're rerunning the script for the same output, you may need to manually delete the temporary files from the previous run.

You can debug a PMTiles file using <https://protomaps.github.io/PMTiles>.

There's a manual step required to generate `--wards` and `--census_output_areas`. See the comment in the code.

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
