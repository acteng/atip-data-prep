use std::io::BufWriter;

use anyhow::Result;
use fs_err::File;
use gdal::vector::LayerAccess;
use gdal::Dataset;
use geojson::{Feature, FeatureWriter};
use indicatif::{ProgressBar, ProgressStyle};

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        panic!("Pass in trn_rami_averageandindicativespeed.gpkg");
    }

    let dataset = Dataset::open(&args[1])?;
    let mut layer = dataset.layer(0)?;

    let progress = ProgressBar::new(layer.feature_count()).with_style(ProgressStyle::with_template(
        "[{elapsed_precise}] [{wide_bar:.cyan/blue}] {human_pos}/{human_len} ({per_sec}, {eta})").unwrap());

    // TODO How's fgb as an intermediate?
    let mut writer = FeatureWriter::from_writer(BufWriter::new(File::create("output.geojson")?));

    for feature in layer.features() {
        progress.inc(1);
        let indicative_mph = feature
            .field_as_integer_by_name("indicativespeedlimit_mph")?
            .unwrap();
        let (worst_kph, worst_description) = highest_speed(&feature)?;

        let mut feature =
            Feature::from(geojson::Value::from(&feature.geometry().unwrap().to_geo()?));
        feature.set_property("indicative_mph", indicative_mph);
        feature.set_property("worst_kph", worst_kph);
        feature.set_property("worst_description", worst_description);

        writer.write_feature(&feature)?;
    }
    Ok(())
}

fn highest_speed(feature: &gdal::vector::Feature) -> Result<(f64, String)> {
    let mut max = None;
    let mut max_key = None;
    for time in [
        "mf4to7", "mf7to9", "mf9to12", "mf12to14", "mf14to16", "mf16to19", "mf19to22", "mf22to4",
        "ss4to7", "ss7to10", "ss14to19", "ss19to22", "ss22to4",
    ] {
        for direction in ["indirection", "againstdirection"] {
            let key = format!("averagespeed_{time}{direction}_kph");
            // TODO Probably could use field indices
            if let Some(value) = feature.field_as_double_by_name(&key)? {
                // TODO Some(0.0) means some other kind of error?!
                if max.map(|n| n < value).unwrap_or(true) {
                    max = Some(value);
                    max_key = Some(key);
                }
            }
        }
    }
    Ok((max.unwrap(), max_key.unwrap()))
}
