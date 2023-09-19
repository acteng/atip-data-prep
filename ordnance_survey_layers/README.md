# Ordnance Survey layer prep

These scripts prepare a layer with road width and speeds from OS data. You need
access to OS DataHub (via the PSGA license or similar), and the resulting
layers must not be published anywhere public.

You'll need to have [Rust](https://www.rust-lang.org/tools/install) and
[tippecanoe](https://github.com/felt/tippecanoe) installed on your system.

You also need to manually download two datasets from OS. Log in to the [OS
DataHub](https://osdatahub.os.uk). Use "OS Select+Build" to create a new recipe
containing two feature types: "Transport > RAMI > Average And Indicative Speed"
and "Transport > Transport Network > Road Link". After creating the recipe, add
a Data Package, choosing WGS84 as the Coordinate Reference System and
GeoPackage as the format.

It may take a few hours before the download is ready. You should download two
separate files, `trn_ntwk_roadlink.zip` and
`trn_rami_averageandindicativespeed.zip`, and unzip them somewhere. There
should be one large `.gpkg` file in each, which you'll use in the commands
below.

To generate the width dataset:

```
# After compiling for the first time, the command itself should take 3-4 minutes
cargo run --release ~/Downloads/ordnance_survey_downloads/trn_ntwk_roadlink.gpkg --layer width
# This will take longer -- about 30 minutes
tippecanoe --drop-densest-as-needed --generate-ids -zg road_widths.geojson -o road_widths.pmtiles -l road_widths
```

And the speed dataset, with similar timings:

```
cargo run --release ~/Downloads/ordnance_survey_downloads/trn_rami_averageandindicativespeed.gpkg --layer speed
tippecanoe --drop-densest-as-needed --generate-ids -zg road_speeds.geojson -o road_speeds.pmtiles -l road_speeds
```

Then upload the final results, `road_widths.pmtiles` and `road_speeds.pmtiles`
to a secure GCS bucket. **Do not put these files, or the input or intermediate
files, anywhere public.**
