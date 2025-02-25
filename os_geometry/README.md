# Ordnance Survey MasterMap geometry layer

The OS MasterMap topo dataset contains precise polygons for roads, junctions, pavements, and other useful features for determining what could fit within the right-of-way. This crate produces a pmtiles file for showing some of these polygons.

## Running it

1.  Download the latest copy of [MasterMap Topo](https://osdatahub.os.uk/downloads/premium/MMTOPO) in mbtiles format for all of GB. It's around 20GB.
2.  Unzip
3.  You'll only need the `TopographicArea.mbtiles` file, which is about 10GB.
4.  `cargo run --release path/to/OSMasterMapTopography_gb_TopographicArea.mbtiles`
5.  Upload `osmm.pmtiles` to `private_layers/v1`. **Note this is a private layer**

## Data source

OSMM topo is available in two formats:

- An mbtiles file covering everywhere, with polygons only at zoom level 16, with each polygon split at tile boundaries. This format is only useful for rendering.
- Geopackage files, much easier for processing and analysis, but only available as individual area extracts.

Due to the difficulty of downloading gpkg files for everywhere, we work with the one mbtiles file.

## Notes on an approach that didn't work, using existing tools

Our goal is to filter the input data for only some road and pavement types, then turn into a pmtiles file for visualization. This is far from straightforward, because:

-  No existing tool seems to have support for filtering mbtiles directly. Internally, this mbtiles file is just a SQLite file, with each tile being vector data compressed and encoded using the MVT protocol buffer format. So filtering requires decompressing and parsing the tile format, which very compactly encodes things like feature properties.
-  `ogr2ogr` doesn't seem to have any support for creating pmtiles
-  tippecanoe is the main tool that can produce pmtiles, and it requires GeoJSON inputs. GeoJSON as a text format is _enormous_ for our scale.
-  ogr2ogr has no working "progress bars", so there's no easy way when processing enormous files to estimate final file sizes or completion times.

An approach that didn't work:

1.  Convert the 10GB mbtiles file into gpkg with ogr2ogr. This takes around 4 hours and yields an 85GB file. (This could maybe be faster and smaller by not building the index, since we don't need it for our ultimate pmtiles use.)
2.  Filter the gpkg for just the polygons we want, taking 6 minutes again using ogr2ogr and producing a 17GB gpkg file.
3.  Use ogr2ogr to turn this into GeoJSON. I gave up when the output was around 200GB.
4.  Use tippecanoe to turn that into tiles. Likely to take hours for clipping features to tiles.

## The approach here

The Rust tool here takes just 10 minutes, producing a 2.6GB pmtiles file as output. It could probably be much faster with parallelization, too.

The key insight is that the input file has already done the hard work of clipping features to tile boundaries. We just want to filter the features encoded in each tile by properties, not touching any of the geometry. PMTiles is just another container format like MBTiles, so repackaging is fast.

The limit here is that the polygons are only visible at zoom 16. It'd be nice to show them farther away, but that _would_ require more work.
