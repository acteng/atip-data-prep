#!/bin/bash

# Assumes split_uk_osm.sh is done

set -e

# Build the importer
cd importer
cargo build --release
cd ..

# Clean anything from a previous import
rm -rf route_info_files
mkdir route_info_files

IFS=$'\n'
for osm in uk_osm/out/*; do
	geojson=$(basename $osm .osm).geojson
	out=$(basename $osm .osm).bin
	task=$(pueue add --print-task-id --working-directory importer --escape cargo run --release -- "../$osm" "../uk_osm/$geojson" "../route_info_files/$out")
	pueue add --after $task --escape gzip "route_info_files/$out"
done

# Manually wait for pueue to finish

# Put in S3
#
# Update "v2" as needed, and change the ATIP code to point to the new version.
# The versioning scheme itself is MAJOR.MINOR, but not too critical, as there
# are usually just 2 or 3 different deployed versions of ATIP at a time.
#

# aws s3 sync --dry --content-encoding="gzip" route_info_files/ s3://atip.uk/route-info/v2/

# Make sure content-encoding is set to gzip for all the bin.gz files.
# You can test if this works: curl --head https://atip.uk/route-info/v2/Derby.bin.gz | grep encoding

# If you've created a new version, you're done. If you overwrote existing
# files, you have to invalidate the CDN manually! Use the S3 console
