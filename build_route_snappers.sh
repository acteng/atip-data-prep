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
# If the same files are going in dev and prod, this saves bandwidth: aws s3 sync --dry s3://atip.uk/route-snappers/ s3://atip.uk/route-snappers-dev/

# Make sure content-encoding is set to gzip for all the bin.gz files.
# TODO On the next big upload, try adding the flag to the sync command above directly
# To fix it after the fact:
#
# aws s3 cp \
#        s3://atip.uk/route-snappers/ \       # or -dev
#        s3://atip.uk/route-snappers/ \       # or -dev
#        --exclude '*' \
#        --include '*.gz' \
#        --no-guess-mime-type \
#        --content-encoding="gzip" \
#        --metadata-directive="REPLACE" \
#        --recursive
#
# You can test if this works: curl --head https://atip.uk/route-snappers/Derby.bin.gz | grep encoding

# Have to invalidate the CDN manually! Use the S3 console
