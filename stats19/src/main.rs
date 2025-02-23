use std::collections::HashMap;

use anyhow::Result;
use fs_err::File;
use geojson::{Feature, Geometry, Value};
use indicatif::{HumanCount, ProgressBar, ProgressStyle};
use serde::Deserialize;

// https://data.dft.gov.uk/road-accidents-safety-data/dft-road-casualty-statistics-road-safety-open-dataset-data-guide-2023.xlsx defines the categorical variables

fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    let only_pedestrians_and_cyclists =
        args.len() == 2 && args[1] == "--only_pedestrians_and_cyclists";

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
        if collision.severities.is_empty() {
            panic!("Unexpected: no casualties matched to accident_index = {accident_index}");
        }

        if only_pedestrians_and_cyclists && !collision.pedestrian && !collision.cyclist {
            continue;
        }

        let mut f = Feature::from(Geometry::new(Value::Point(vec![
            collision.lon,
            collision.lat,
        ])));
        f.set_property("accident_index", accident_index);
        f.set_property("year", collision.year);
        f.set_property("pedestrian", collision.pedestrian);
        f.set_property("cyclist", collision.cyclist);
        if !only_pedestrians_and_cyclists {
            f.set_property("horse_rider", collision.horse_rider);
            f.set_property("other", collision.other);
        }
        f.set_property("pedestrian_location", collision.pedestrian_location);
        f.set_property("pedestrian_movement", collision.pedestrian_movement);
        // Just output the worst severity. 1 = fatal, 2 = serious, 3 = slight
        f.set_property("severity", collision.severities.into_iter().min().unwrap());
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

        // Only keep the most recent 6 years (and the dataset only covers up to 2023 right now)
        if rec.accident_year < 2017 {
            continue;
        }

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
                severities: Vec::new(),
                pedestrian: false,
                cyclist: false,
                horse_rider: false,
                other: false,
                // 0 means "not a pedestrian", so it's a good default before we fill this out
                pedestrian_movement: 0,
                pedestrian_location: 0,
            },
        );
    }
    progress.finish();
    println!(
        "Got {} collisions, and skipped {} invalid (but recent) records",
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
                collision.severities.push(rec.casualty_severity);

                if rec.casualty_type == 0 || rec.casualty_type == 22 {
                    // Mobility scooter riders also count here
                    collision.pedestrian = true;
                } else if rec.casualty_type == 1 {
                    collision.cyclist = true;
                } else if rec.casualty_type == 16 {
                    collision.horse_rider = true;
                } else {
                    // The rest all involve motor vehicle drivers/passengers
                    collision.other = true;
                }

                // Skip useless values: 0 is "not a pedestrian", -1 is "data missing", 10 is
                // "unknown or other"
                if rec.pedestrian_location != 0
                    && rec.pedestrian_location != -1
                    && rec.pedestrian_location != 10
                {
                    collision.pedestrian_location = rec.pedestrian_location;
                }
                // Skip useless values: 0 is "not a pedestrian", -1 is "data missing", 9 is
                // "unknown or other"
                if rec.pedestrian_movement != 0
                    && rec.pedestrian_movement != -1
                    && rec.pedestrian_movement != 9
                {
                    collision.pedestrian_movement = rec.pedestrian_movement;
                }
            }
            None => {
                //println!("Skipping casualty with accident_index {accident_index}");
                skipped += 1;
            }
        }
    }
    progress.finish();
    println!(
        "Skipped {} casualty records that didn't match to a collision",
        HumanCount(skipped as u64)
    );

    Ok(collisions)
}

// The summarized event
struct Collision {
    year: usize,
    lon: f64,
    lat: f64,

    severities: Vec<usize>,
    // At least one
    pedestrian: bool,
    cyclist: bool,
    horse_rider: bool,
    other: bool,

    // If there are multple pedestrian casualties in one collision, these details come from one of
    // them arbitrarily
    pedestrian_movement: isize,
    pedestrian_location: isize,
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
    casualty_type: isize,
    pedestrian_location: isize,
    pedestrian_movement: isize,
}
