# ATIP data prep

This repo has some scripts to import data required by ATIP.

The sections below describe different portions of the repo. Files/directories not covered below include:

- `authorities.geojson` has a Polygon boundary for every Local Authority District and Transport Authority
  - The data comes from https://github.com/acteng/boundaries, and then
    `fix_boundaries` is used to turn MultiPolygons into a single Polygon with
    convex hull.

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

## Creating authorities.geojson

The Scheme Sketcher and route-snapper works in one area at a time. Those areas are defined by `authorities.geojson` in this repo and in [atip](https://github.com/acteng/atip). To generate this file:

1.  Download the GeoJSON file from <https://geoportal.statistics.gov.uk/datasets/ons::local-authority-districts-may-2023-boundaries-uk-bfe/explore> and rename the file to `layers/input/lads.geojson`
2.  Download <https://github.com/acteng/boundaries/blob/main/transport_authorities.geojson> and rename the file to `layers/input/transport_authorities.geojson`
3.  `cd layers; ./generate_layers.py --local_authorities_for_sketcher --transport_authorities_for_sketcher`
4.  `mkdir -p ../fix_boundaries/input/; mv output/local_authority_districts_reprojected.geojson output/transport_authorities_reprojected.geojson ../fix_boundaries/input/`
5.  `cd ../fix_boundaries; npm run run`
6.  Copy `output/authorities.geojson` to the root of this repo and commit, and also copy to the atip repo in `assets/`. You'll probably need to run the steps below to regenerate route snapper files.

## Splitting huge OSM files

The route snapper pipeline needs two files as input: an OSM PBF file and a
GeoJSON file with a single polygon, representing the area clipped in that OSM
file. For ATIP, we want to repeat this for every LAD and TA in the UK.

To run this:

1.  Ensure `authorities.geojson` is up-to-date if needed, using the process above
2.  Make sure you have about 3GB of disk free
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

1.  Set up the submodules in this repo: `git submodule init && git submodule update`
2.  Complete the section above to split OSM files
3.  Make sure the pueue daemon is started, and tasks cleared out. (`pueued -d; pueue status; pueue clean`)
4.  Run `./build_route_snappers.sh`
5.  Wait for all pueue commands to succeed (`pueue status`)
6.  Manually upload to S3, following instructions in that script

To update to a newer commit in the [route-snapper
repo](https://github.com/dabreegster/route_snapper), run `git submodule update
--remote`.

## Extra contextual layers

ATIP can display extra contextual layers:

- Data from OpenStreetMap
  - Points of interest, like schools, hospitals, sports centres, etc
  - Roads with bus lanes and bus routes
  - Cycle parking
  - Existing cycle paths
  - Crossings
  - Tram lines
- the [Major Road Network](https://www.data.gov.uk/dataset/95f58bfa-13d6-4657-9d6f-020589498cfd/major-road-network)
- Boundaries
  - Parliament constituency boundaries, from [OS Boundary-Line](https://www.ordnancesurvey.co.uk/products/boundary-line)
  - Wards, from [OS and ONS](https://geoportal.statistics.gov.uk/datasets/ons::wards-may-2023-boundaries-uk-bgc/explore)
  - Combined authorities from [OS and ONS](https://geoportal.statistics.gov.uk/datasets/ons::combined-authorities-december-2022-boundaries-en-buc/explore)
  - Local authority districts from [OS and ONS](https://geoportal.statistics.gov.uk/datasets/ons::local-authority-districts-may-2023-boundaries-uk-buc/explore)
  - Local planning authorities from [planning.data.gov.uk](https://www.planning.data.gov.uk/dataset/local-planning-authority)
- Output-area level 2021 census data
	- Output area boundaries from [OS and ONS](https://geoportal.statistics.gov.uk/datasets/ons::output-areas-2021-boundaries-ew-bgc/explore)
	- Population density comes from [NOMIS TS006](https://www.nomisweb.co.uk/sources/census_2021_bulk)
	- Car/van availability comes from [NOMIS TS045](https://www.nomisweb.co.uk/sources/census_2021_bulk)
- LSOA level 2011 census data
	- Indices of Multiple Deprivation comes from [DLUCH](https://data-communities.opendata.arcgis.com/datasets/communities::indices-of-multiple-deprivation-imd-2019-1/explore)
- Traffic counts from [DfT](https://roadtraffic.dft.gov.uk/downloads)
- 2011 [Propensity to Cycle Tool route network data](https://github.com/npct/pct-outputs-national)

These layers are England-wide, rather than being split into a file per area,
because they're being used on the country-wide scheme browse page. Each layer
is a single GeoJSON file if it's small enough, or
[PMTiles](https://protomaps.com/docs/pmtiles/) for larger ones.

To run this:

1.  Get `england-latest.osm.pbf` from Geofabrik. The `split_uk_osm.sh` script above does this.
2.  Run `cd layers; ./generate_layers.py --osm_input=../england-latest.osm.pbf --education --hospitals --mrn --parliamentary_constituencies --combined_authorities --local_authority_districts --local_planning_authorities --sports_spaces --railway_stations --bus_routes --crossings --cycle_parking --cycle_paths --ncn --wards --vehicle_counts --pct --local_authorities_for_sketcher --transport_authorities_for_sketcher --trams`
3.  Pick an arbitrary version number, and upload the files: `for x in output/*; do aws s3 cp --dry $x s3://atip.uk/layers/v1/; done`

If you're rerunning the script for the same output, you may need to manually delete the output files from the previous run.

You can debug a PMTiles file using <https://protomaps.github.io/PMTiles>.

There's a manual step required to generate `--census_output_areas` and `--imd`. See the comment in the code.

For `--cycle_paths`, you'll need about 20GB of RAM, until we switch to a streaming JSON parser.

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

## Manifest

The `MANIFEST.txt` file records files currently hosted in the test GCS bucket. When someone uploads a file there, please update this file, so it's easier to check if the current state of the bucket diverges from a known state.

To generate it, change the project ID as needed and run:

```
gsutil ls -rl gs://dft-rlg-atip-{env}/** > MANIFEST-{ENV}.txt
```
