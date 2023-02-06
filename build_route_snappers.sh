#!/bin/bash

# Assumes split_uk_osm.sh is done

# Note each pueue command runs independently, and you have to manually wait for
# them and check status
set -e

cd route_snapper/osm-to-route-snapper
cargo build --release
cd ../../
bin=./route_snapper/osm-to-route-snapper/target/release/osm-to-route-snapper

mkdir -p route-snappers

IFS=$'\n'
for osm in uk_osm/out/*; do
	geojson=$(basename $osm .osm).geojson
	out=$(basename $osm .osm).bin
	pueue add --escape $bin -i "$osm" -b "uk_osm/$geojson" -o "route-snappers/$out"
done

# Put in S3
# prod: aws s3 sync --dry route-snappers s3://atip.uk/route-snappers/
# dev: aws s3 sync --dry route-snappers s3://atip.uk/route-snappers-dev/

# Have to invalidate the CDN manually! Use the S3 console
