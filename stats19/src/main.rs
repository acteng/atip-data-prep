use std::collections::HashMap;

use anyhow::Result;
use fs_err::File;
use geojson::{Feature, Geometry, Value};
use indicatif::{HumanCount, ProgressBar, ProgressStyle};
use serde::Deserialize;

fn main() -> Result<()> {
    let collisions = read_input()?;

    // Write a GeoJSON with one point per collision
    println!("Writing GeoJSON");
    let mut writer = geojson::FeatureWriter::from_writer(std::io::BufWriter::new(
        fs_err::File::create("tmp/stats19.geojson")?,
    ));
    let progress = ProgressBar::new(collisions.len() as u64).with_style(ProgressStyle::with_template(
            "[{elapsed_precise}] [{wide_bar:.cyan/blue}] {human_pos}/{human_len} ({per_sec}, {eta})").unwrap());
    for (accident_index, collision) in collisions {
        progress.inc(1);
        if collision.casualties.is_empty() {
            panic!("Unexpected: no casualties matched to accident_index = {accident_index}");
        }

        let mut f = Feature::from(Geometry::new(Value::Point(vec![
            collision.lon,
            collision.lat,
        ])));
        f.set_property("year", collision.year);
        f.set_property("num_casualties", collision.casualties.len());
        // Just output the worst severity
        f.set_property("severity", collision.casualties.into_iter().min().unwrap());
        writer.write_feature(&f)?;
    }
    progress.finish();

    Ok(())
}

/// Reads and links collisions and casualties, returning a mapping from accident_index to the
/// summarized Collision.
fn read_input() -> Result<HashMap<String, Collision>> {
    println!("Reading collisions");
    // Map accident_index to Collision
    let mut collisions = HashMap::new();
    let mut skipped = 0;
    let progress = ProgressBar::new_spinner().with_style(
        ProgressStyle::with_template("[{elapsed_precise}] {human_len} records read ({per_sec})")
            .unwrap(),
    );
    for rec in csv::Reader::from_reader(File::open(
        "input/dft-road-casualty-statistics-collision-1979-latest-published-year.csv",
    )?)
    .deserialize()
    {
        progress.inc(1);
        let rec: CollisionRow = rec?;
        if rec.location_easting_osgr == "NULL" || rec.location_northing_osgr == "NULL" {
            skipped += 1;
            continue;
        }
        let easting: f64 = rec.location_easting_osgr.parse()?;
        let northing: f64 = rec.location_northing_osgr.parse()?;
        let Ok((lon, lat)) = lonlat_bng::convert_osgb36_to_ll(easting, northing) else {
            //println!("Skipping collision with BNG coordinates {easting}, {northing}");
            skipped += 1;
            continue;
        };
        collisions.insert(
            rec.accident_index,
            Collision {
                year: rec.accident_year,
                lon,
                lat,
                casualties: Vec::new(),
            },
        );
    }
    progress.finish();
    println!(
        "Got {} collisions, and skipped {} invalid records",
        HumanCount(collisions.len() as u64),
        HumanCount(skipped as u64)
    );

    println!("Reading casualties");
    skipped = 0;
    progress.reset();
    for rec in csv::Reader::from_reader(File::open(
        "input/dft-road-casualty-statistics-casualty-1979-latest-published-year.csv",
    )?)
    .deserialize()
    {
        progress.inc(1);
        let rec: CasualtyRow = rec?;
        match collisions.get_mut(&rec.accident_index) {
            Some(collision) => {
                collision.casualties.push(rec.casualty_severity);
            }
            None => {
                //println!("Skipping casualty with accident_index {accident_index}");
                skipped += 1;
            }
        }
    }
    progress.finish();
    println!("Skipped {} invalid casualty records", HumanCount(skipped as u64));

    Ok(collisions)
}

// The summarized event
struct Collision {
    year: usize,
    lon: f64,
    lat: f64,
    // Per https://data.dft.gov.uk/road-accidents-safety-data/dft-road-casualty-statistics-road-safety-open-dataset-data-guide-2023.xlsx, 1 = fatal, 2 = serious, 3 = slight
    casualties: Vec<usize>,
}

// These two are for parsing subsets of the CSV inputs
#[derive(Deserialize)]
struct CollisionRow {
    accident_index: String,
    accident_year: usize,
    // To handle the hassle of "NULL", just parse to f64 manually
    location_easting_osgr: String,
    location_northing_osgr: String,
}

#[derive(Deserialize)]
struct CasualtyRow {
    accident_index: String,
    casualty_severity: usize,
}
