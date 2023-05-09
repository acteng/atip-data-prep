#!/bin/bash

# Assumes split_uk_osm.sh is done

set -e

# Build the importer
cd abstreet
./import.sh
# Clean anything from a previous import
rm -rf data/system/zz/oneshot/maps/
cd ..

IFS=$'\n'
for osm in uk_osm/out/*; do
	geojson=$(basename $osm .osm).geojson
	pueue add -w abstreet --escape ./target/release/cli oneshot-import "../$osm" --clip-path "../uk_osm/$geojson" --skip-ch
done

# Manually wait for pueue to finish

# Put in S3
# prod: aws s3 sync --dry abstreet/data/system/zz/oneshot/maps/ s3://atip.uk/route-info/
# dev: aws s3 sync --dry abstreet/data/system/zz/oneshot/maps/ s3://atip.uk/route-info-dev/
# If the same files are going in dev and prod, this saves bandwidth: aws s3 sync --dry s3://atip.uk/route-info/ s3://atip.uk/route-info-dev/

# Have to invalidate the CDN manually! Use the S3 console
