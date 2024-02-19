#!/bin/bash

set -e

mkdir -p input
if [ ! -e "input/UK-dem-50m-4326.tif" ]; then
	wget https://play.abstreet.org/dev/data/input/shared/elevation/UK-dem-50m-4326.tif.gz -P input
	gunzip input/UK-dem-50m-4326.tif.gz
fi

mkdir -p tmp
# Assume the root directory has the osm.pbf, used by many other scripts in this repo
time cargo run --release ../england-latest.osm.pbf input/UK-dem-50m-4326.tif

time tippecanoe tmp/gradient.geojson \
	--force \
	--generate-ids \
	-l gradient \
	-zg \
	--drop-densest-as-needed \
	--extend-zooms-if-still-dropping \
	-o gradient.pmtiles
