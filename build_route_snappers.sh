#!/bin/bash

# Assumes split_uk_osm.sh is done

set -e

# Build the import tool
cd route_snapper/osm-to-route-snapper
cargo build --release
cd ../../
bin=./route_snapper/osm-to-route-snapper/target/release/osm-to-route-snapper

mkdir -p route-snappers

IFS=$'\n'
for osm in uk_osm/out/*; do
	geojson=$(basename $osm .osm).geojson
	out=$(basename $osm .osm).bin
	task=$(pueue add --print-task-id --escape $bin -i "$osm" -b "uk_osm/$geojson" -o "route-snappers/$out")
	pueue add --after $task --escape gzip "route-snappers/$out"
done

# Manually wait for pueue to finish

# Put in S3
# prod: aws s3 sync --dry route-snappers s3://atip.uk/route-snappers/
# dev: aws s3 sync --dry route-snappers s3://atip.uk/route-snappers-dev/

# Have to invalidate the CDN manually! Use the S3 console
