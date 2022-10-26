#!/bin/bash

set -e

mkdir uk_osm
cd uk_osm
mkdir out
../geojson_to_osmium_extracts.py ../authorities.geojson --name_key=Name --output_dir=out/ --batch_size=2

for batch in osmium_cfg_*; do
	time osmium extract -v -c $batch ~/Downloads/england-latest.osm.pbf
done
