#!/bin/bash

set -e

mkdir uk_osm
cd uk_osm
mkdir out
../geojson_to_osmium_extracts.py ../authorities.geojson --name_key=Name --output_dir=out/ --batch_size=2

for batch in osmium_cfg_*; do
	time osmium extract -v -c $batch ~/Downloads/england-latest.osm.pbf
done

# Generate route snapper files
cd ..
IFS=$'\n'
for x in uk_osm/out/*; do
	geojson=$(basename $x .osm).geojson
	cargo run --release $x uk_osm/$geojson
done
# Put in S3
mkdir route-snappers
mv *.bin route-snappers
aws s3 sync --dry route-snappers s3://abstreet/route-snappers/
