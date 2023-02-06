#!/bin/bash

# Assumes split_uk_osm.sh is done

# Don't enable this; better to best-effort as many places as possible
#set -e

cd route_snapper/osm-to-route-snapper
cargo build --release
cd ../../
# Note the x86_64 architecture part might not be true on your system
bin=./route_snapper/osm-to-route-snapper/target/x86_64-unknown-linux-gnu/release/osm-to-route-snapper

mkdir -p route-snappers

IFS=$'\n'
for x in uk_osm/out/*; do
	geojson=$(basename $x .osm).geojson
	pueue add --escape $bin "$x" "uk_osm/$geojson"
done

# Put in S3
#mv *.bin route-snappers
#aws s3 sync --dry route-snappers s3://atip.uk/route-snappers/

# Have to invalidate the CDN manually! Use the S3 console
