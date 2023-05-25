t!/bin/bash

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
# prod: aws s3 sync --dry route_info_files/ s3://atip.uk/route-info/
# dev: aws s3 sync --dry route_info_files/ s3://atip.uk/route-info-dev/
# If the same files are going in dev and prod, this saves bandwidth: aws s3 sync --dry s3://atip.uk/route-info/ s3://atip.uk/route-info-dev/

# Have to invalidate the CDN manually! Use the S3 console
