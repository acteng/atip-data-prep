# OSM cycle routes

This generates a layer with cycle routes according to OSM.

```shell
cargo run --release ../england-latest.osm.pbf

time tippecanoe cycle_routes.geojson \
  --force \
  --generate-ids \
  -l cycle_routes \
  -zg \
  --drop-densest-as-needed \
  --extend-zooms-if-still-dropping \
  -o cycle_routes.pmtiles
```

