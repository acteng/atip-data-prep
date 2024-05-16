use std::collections::HashMap;
use std::io::BufWriter;

use anyhow::Result;
use fs_err::File;
use gdal::vector::LayerAccess;
use gdal::Dataset;
use geo::{Coord, Geometry, HaversineBearing, MapCoordsInPlace};
use geojson::FeatureWriter;
use indicatif::{ProgressBar, ProgressStyle};

struct Road {
    geometry: Geometry,
    angle: isize,
    left: Option<(f64, f64)>,
    right: Option<(f64, f64)>,
}

pub fn process(input_path: &str, output_path: &str) -> Result<()> {
    let dataset = Dataset::open(input_path)?;
    // Assume only one layer
    let mut layer = dataset.layer(0)?;

    println!("Reading and joining input");
    let mut progress = ProgressBar::new(layer.feature_count()).with_style(ProgressStyle::with_template(
        "[{elapsed_precise}] [{wide_bar:.cyan/blue}] {human_pos}/{human_len} ({per_sec}, {eta})").unwrap());

    // Keyed by roadlinkid
    let mut roads: HashMap<String, Road> = HashMap::new();

    // Each road might have two separate input features for each side of the road. First read in
    // and join all the data. This only takes about 2GB of memory.
    for input_feature in layer.features() {
        progress.inc(1);

        let average = input_feature.field_as_double_by_name("presenceofpavement_averagewidth_m")?;
        let minimum = input_feature.field_as_double_by_name("presenceofpavement_minimumwidth_m")?;
        let side = input_feature.field_as_string_by_name("presenceofpavement_sideofroad")?;

        let (Some(average), Some(minimum), Some(side)) = (average, minimum, side) else {
            continue;
        };
        // If they're both 0, don't show anything
        if average == 0.0 && minimum == 0.0 {
            continue;
        }

        let roadlinkid = input_feature
            .field_as_string_by_name("roadlinkid")?
            .expect("missing roadlinkid");
        let road = roads.entry(roadlinkid).or_insert_with(|| {
            let mut geometry = input_feature
                .geometry()
                .unwrap()
                .to_geo()
                .expect("converting to geo broke");
            // Remove unnecessary precision
            geometry.map_coords_in_place(|Coord { x, y }| Coord {
                x: trim_f64(x),
                y: trim_f64(y),
            });
            let angle = if let Geometry::LineString(ls) = &geometry {
                let bearing = ls
                    .points()
                    .next()
                    .unwrap()
                    .haversine_bearing(ls.points().last().unwrap())
                    .round() as isize;
                (bearing + 360) % 360
            } else {
                panic!("Not a LineString");
            };

            Road {
                geometry,
                angle,
                left: None,
                right: None,
            }
        });
        if side == "Right" {
            road.right = Some((average, minimum));
        } else {
            road.left = Some((average, minimum));
        }
    }

    // Then output all the joined data.
    println!("Writing output");
    let mut writer = FeatureWriter::from_writer(BufWriter::new(File::create(output_path)?));
    progress = ProgressBar::new(roads.len() as u64).with_style(ProgressStyle::with_template(
        "[{elapsed_precise}] [{wide_bar:.cyan/blue}] {human_pos}/{human_len} ({per_sec}, {eta})").unwrap());

    for road in roads.into_values() {
        progress.inc(1);
        let mut output_feature = geojson::Feature::from(geojson::Value::from(&road.geometry));
        output_feature.set_property("angle", road.angle);
        if let Some((average, minimum)) = road.left {
            output_feature.set_property("left_average", average);
            output_feature.set_property("left_minimum", minimum);
        }
        if let Some((average, minimum)) = road.right {
            output_feature.set_property("right_average", average);
            output_feature.set_property("right_minimum", minimum);
        }
        writer.write_feature(&output_feature)?;
    }

    Ok(())
}

fn trim_f64(x: f64) -> f64 {
    (x * 10e6).round() / 10e6
}
