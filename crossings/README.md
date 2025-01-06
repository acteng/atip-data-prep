# Crossings

This generates a crossings layer from OSM data.

```shell
cargo run --release ../england-latest.osm.pbf

time tippecanoe crossings.geojson \
  --force \
  --generate-ids \
  -l crossings \
  -zg \
  --drop-densest-as-needed \
  --extend-zooms-if-still-dropping \
  -o crossings.pmtiles
```
