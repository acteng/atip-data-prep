use std::f64::consts::PI;
use std::fs::File;
use std::io::{BufWriter, Cursor, Read, Write};

use anyhow::Result;
use geozero::mvt::{tile::Layer, Message};
use indicatif::{ProgressBar, ProgressStyle};
use mbtiles::Mbtiles;
use pmtiles2::{util::tile_id, Compression, PMTiles, TileType};

/// This script takes the `OSMasterMapTopography_gb_TopographicArea.mbtiles` file as input, filters for features with the "Roads Tracks And Paths" theme, and re-encodes as pmtiles.
#[tokio::main]
async fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    let path = &args[1];
    println!("Opening {path}");

    let mbtiles = Mbtiles::new(path)?;
    let mut conn = mbtiles.open_readonly().await?;

    let metadata = mbtiles.get_metadata(&mut conn).await?;
    let bounds = metadata.tilejson.bounds.unwrap();
    // TODO Could read as the minzoom/maxzoom, which should be the same
    let zoom = 16_u8;
    let (x1, y1) = lon_lat_to_tile(bounds.left, bounds.top, zoom.into());
    let (x2, y2) = lon_lat_to_tile(bounds.right, bounds.bottom, zoom.into());
    println!("Reading x = {x1} to {x2}, y = {y1} to {y2}");

    let mut pmtiles = PMTiles::new(TileType::Mvt, Compression::GZip);
    pmtiles.min_longitude = bounds.left;
    pmtiles.min_latitude = bounds.bottom;
    pmtiles.max_longitude = bounds.right;
    pmtiles.max_latitude = bounds.top;
    pmtiles.min_zoom = zoom;
    pmtiles.max_zoom = zoom;
    pmtiles.meta_data.insert(
        "vector_layers".to_string(),
        serde_json::json!([
            {
                "id": "topographic_area",
                "minzoom": zoom,
                "maxzoom": zoom,
                "fields": {
                    "toid": "String",
                    "style_description": "String",
                    "style_code": "Number",
                },
            }
        ]),
    );

    let progress = ProgressBar::new(((x2 - x1 + 1) * (y2 - y1 + 1)).into()).with_style(ProgressStyle::with_template(
        "[{elapsed_precise}] [{wide_bar:.cyan/blue}] {human_pos}/{human_len} ({per_sec}, {eta})").unwrap());

    // TODO This should be parallelizable with rayon
    for tile_x in x1..=x2 {
        for tile_y in y1..=y2 {
            progress.inc(1);

            match mbtiles.get_tile(&mut conn, zoom, tile_x, tile_y).await {
                Ok(Some(bytes)) => {
                    // Decompress and parse the tile
                    let mut decoder = flate2::read::GzDecoder::new(Cursor::new(bytes));
                    let mut gunzipped = Vec::new();
                    decoder.read_to_end(&mut gunzipped)?;
                    let mut tile = geozero::mvt::Tile::decode(Cursor::new(gunzipped))?;

                    // Process the tile, filtering for features we care about. Drop tiles with no
                    // matches. (Note there's just one layer per tile; the loop below is kind of
                    // pointless.)
                    let mut ok = false;
                    for layer in &mut tile.layers {
                        process_mvt_layer(layer);
                        ok = ok || !layer.features.is_empty();
                    }

                    if ok {
                        // Re-compress and re-encode it, and package up in pmtiles
                        let mut tile_bytes = Vec::new();
                        let mut encoder = flate2::write::GzEncoder::new(
                            &mut tile_bytes,
                            flate2::Compression::best(),
                        );
                        encoder.write_all(&tile.encode_to_vec())?;
                        encoder.finish()?;

                        pmtiles
                            .add_tile(tile_id(zoom, tile_x.into(), tile_y.into()), tile_bytes)?;
                    }
                }
                Ok(None) => {}
                Err(err) => {
                    println!("Error for {tile_x}, {tile_y}: {err}");
                }
            }
        }
    }
    progress.finish();

    println!("Writing");
    let mut file = BufWriter::new(File::create("osmm.pmtiles")?);
    pmtiles.to_writer(&mut file)?;

    Ok(())
}

// Thanks to https://github.com/MilesMcBain/slippymath/blob/master/R/slippymath.R
// Use https://crates.io/crates/tile-grid or something instead?
// Alternatively https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Python
fn lon_lat_to_tile(lon: f64, lat: f64, zoom: u32) -> (u32, u32) {
    let lon_radians = lon.to_radians();
    let lat_radians = lat.to_radians();

    let x = lon_radians;
    let y = lat_radians.tan().asinh();

    let x = (1.0 + (x / PI)) / 2.0;
    let y = (1.0 - (y / PI)) / 2.0;

    let num_tiles = 2u32.pow(zoom) as f64;

    (
        (x * num_tiles).floor() as u32,
        (y * num_tiles).floor() as u32,
    )
}

fn process_mvt_layer(layer: &mut Layer) {
    layer.features.retain(|feature| {
        // See https://github.com/georust/geozero/blob/c8a5f9103fc5ecc0ae9c7fcd2663b094e620da38/geozero/src/mvt/mvt_reader.rs#L33. We don't need a nice API for this; just look for one particular key/value pair.
        feature.tags.chunks(2).any(|pair| {
            let key = &layer.keys[pair[0] as usize];
            let value = &layer.values[pair[1] as usize];
            key == "theme" && value.string_value() == "Roads Tracks And Paths"
        })
    });

    // TODO We really only need the style_code property. We could drop the others, but we'd have to
    // properly rebuild the tile.
}
