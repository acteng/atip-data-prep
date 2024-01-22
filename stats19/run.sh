#!/bin/bash

set -e

mkdir -p input
# URLs from https://www.data.gov.uk/dataset/cb7ae6f0-4be6-4935-9277-47e5ce24a11f/road-safety-data
if [ ! -e "input/dft-road-casualty-statistics-casualty-1979-latest-published-year.csv" ]; then
	wget https://data.dft.gov.uk/road-accidents-safety-data/dft-road-casualty-statistics-casualty-1979-latest-published-year.csv -P input
fi
if [ ! -e "input/dft-road-casualty-statistics-collision-1979-latest-published-year.csv" ]; then
	wget https://data.dft.gov.uk/road-accidents-safety-data/dft-road-casualty-statistics-collision-1979-latest-published-year.csv -P input
fi

mkdir -p tmp
time cargo run --release

time tippecanoe tmp/stats19.geojson \
	--force \
	--generate-ids \
	-l stats19 \
	-zg \
	--drop-densest-as-needed \
	--extend-zooms-if-still-dropping \
	-o stats19.pmtiles
