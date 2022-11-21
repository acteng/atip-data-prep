#!/bin/bash

# Assumes split_uk_osm.sh is done

# Don't enable this; better to best-effort as many places as possible
#set -e

cargo build --release
mkdir -p route-snappers

IFS=$'\n'
for x in uk_osm/out/*; do
	geojson=$(basename $x .osm).geojson
	cargo run --release $x uk_osm/$geojson
	mv *.bin route-snappers
done

# Put in S3
aws s3 sync --dry route-snappers s3://abstreet/route-snappers/

# Have to invalidate the CDN
# Go to https://us-east-1.console.aws.amazon.com/cloudfront/v3/home?region=us-east-2#/distributions/ER5B3SJO4ND9D/invalidations/create
# TODO Or fix IAM permissions and just: aws cloudfront create-invalidation --distribution-id ER5B3SJO4ND9D --paths '/route-snappers/*
