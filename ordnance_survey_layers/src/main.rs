mod speed;
mod width;

use std::io::BufWriter;

use anyhow::Result;
use fs_err::File;
use gdal::vector::LayerAccess;
use gdal::Dataset;
use geo::{Coord, MapCoordsInPlace};
use geojson::FeatureWriter;
use indicatif::{ProgressBar, ProgressStyle};

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        panic!("Pass in trn_rami_averageandindicativespeed.gpkg");
    }

    gpkg_to_geojson(&args[1], "road_speeds.geojson", speed::speed_properties)
    //gpkg_to_geojson(&args[1], "road_widths.geojson", width::width_properties)

    // time tippecanoe --drop-densest-as-needed --generate-ids -zg road_speeds.geojson -o road_speeds.pmtiles -l road_speeds
    // time tippecanoe --drop-densest-as-needed --generate-ids -zg widths.geojson -o widths.pmtiles -l road_widths
}

fn gpkg_to_geojson<F: Fn(&gdal::vector::Feature, &mut geojson::Feature) -> Result<bool>>(
    input_path: &str,
    output_path: &str,
    extract_properties: F,
) -> Result<()> {
    let dataset = Dataset::open(input_path)?;
    // Assume only one layer
    let mut layer = dataset.layer(0)?;

    let progress = ProgressBar::new(layer.feature_count()).with_style(ProgressStyle::with_template(
        "[{elapsed_precise}] [{wide_bar:.cyan/blue}] {human_pos}/{human_len} ({per_sec}, {eta})").unwrap());

    let mut writer = FeatureWriter::from_writer(BufWriter::new(File::create(output_path)?));

    let mut count = 0;
    for input_feature in layer.features() {
        progress.inc(1);
        let mut geo = input_feature.geometry().unwrap().to_geo()?;
        // Remove unnecessary precision
        geo.map_coords_in_place(|Coord { x, y }| Coord {
            x: trim_f64(x),
            y: trim_f64(y),
        });

        let mut output_feature = geojson::Feature::from(geojson::Value::from(&geo));

        if extract_properties(&input_feature, &mut output_feature)? {
            writer.write_feature(&output_feature)?;
        }
        // TODO tmp
        count += 1;
        if count == 1000000 {
            break;
        }
    }
    Ok(())
}

fn trim_f64(x: f64) -> f64 {
    (x * 10e6).round() / 10e6
}
