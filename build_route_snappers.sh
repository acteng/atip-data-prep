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
	geojson=$(basename $osm .osm.pbf).geojson
	out=$(basename $osm .osm.pbf).bin
	task=$(pueue add --print-task-id --escape $bin --input "$osm" --boundary "uk_osm/$geojson" --output "route-snappers/$out")
	pueue add --after $task --escape gzip "route-snappers/$out"
done

# Manually wait for pueue to finish

# Put in S3
#
# Update "v2" as needed, and change the ATIP code to point to the new version.
# The versioning scheme itself is MAJOR.MINOR, but not too critical, as there
# are usually just 2 or 3 different deployed versions of ATIP at a time.
#

# aws s3 sync --dry --content-encoding="gzip" route-snappers s3://atip.uk/route-snappers/v2/

# Make sure content-encoding is set to gzip for all the bin.gz files.
# You can test if this works: curl --head https://atip.uk/route-snappers/v2/Derby.bin.gz | grep encoding

# If you've created a new version, you're done. If you overwrote existing
# files, you have to invalidate the CDN manually! Use the S3 console
