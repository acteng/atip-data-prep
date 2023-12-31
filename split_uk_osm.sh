#!/bin/bash

set -e

if [ ! -f england-latest.osm.pbf ]; then
	wget http://download.geofabrik.de/europe/great-britain/england-latest.osm.pbf
fi

mkdir uk_osm
cd uk_osm
mkdir out
../geojson_to_osmium_extracts.py ../authorities.geojson --output_dir=out/ --batch_size=10

for batch in osmium_cfg_*; do
	time osmium extract -v -c $batch ../england-latest.osm.pbf
done
