use std::collections::BTreeMap;

use anyhow::Result;
use chrono::{Duration, NaiveTime};
use fs_err::File;
use geojson::{Feature, Geometry, Value};
use serde::Deserialize;

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    if args.len() != 3 {
        panic!("Call with the path to stops.txt and stop_times.txt");
    }

    let mut stops: BTreeMap<String, Stop> = BTreeMap::new();
    println!("Scraping stops");
    for rec in csv::Reader::from_reader(File::open(&args[1])?).deserialize() {
        let rec: StopRow = rec?;
        stops.insert(
            rec.stop_id,
            Stop {
                name: rec.stop_name,
                lon: rec.stop_lon,
                lat: rec.stop_lat,
                times: Vec::new(),
            },
        );
    }

    println!("Scraping stop times");
    let mut scraped = 0;
    let mut skipped = 0;
    for rec in csv::Reader::from_reader(File::open(&args[2])?).deserialize() {
        let rec: StopTimeRow = rec?;
        let Ok(arrival_time) = NaiveTime::parse_from_str(&rec.arrival_time, "%H:%M:%S") else {
            // TODO Handle times > 24 hours, or just ignore, since that's very unlikely to be the
            // peak
            //println!("Weird arrival_time {}", rec.arrival_time);
            skipped += 1;
            continue;
        };
        stops
            .get_mut(&rec.stop_id)
            .unwrap()
            .times
            .push(arrival_time);
        scraped += 1;
    }
    println!("Got {scraped} times, skipped {skipped}");

    println!("Finding peaks");
    let mut writer = geojson::FeatureWriter::from_writer(std::io::BufWriter::new(File::create(
        "stops.geojson",
    )?));
    for (stop_id, stop) in stops {
        if stop.times.is_empty() {
            continue;
        }

        let total_stops = stop.times.len();
        let peak = sliding_window_peak(stop.times, Duration::hours(1));

        let mut f = Feature::from(Geometry::new(Value::Point(vec![stop.lon, stop.lat])));
        f.set_property("stop_id", stop_id);
        f.set_property("stop_name", stop.name);
        f.set_property("total_stops", total_stops);
        f.set_property("peak", peak);
        writer.write_feature(&f)?;
    }

    Ok(())
}

struct Stop {
    name: String,
    lon: f64,
    lat: f64,
    times: Vec<NaiveTime>,
}

#[derive(Deserialize)]
struct StopTimeRow {
    arrival_time: String,
    stop_id: String,
}

#[derive(Deserialize)]
struct StopRow {
    stop_id: String,
    stop_name: String,
    stop_lon: f64,
    stop_lat: f64,
}

// TODO Quasi off-by-ones
fn sliding_window_peak(mut times: Vec<NaiveTime>, window_size: Duration) -> usize {
    times.sort();

    for (idx, t) in times.iter().enumerate() {
        //println!("- {idx}: {t}");
    }

    let mut start_idx = 0;
    let mut end_idx = 0;
    let mut max_count = 0;

    while start_idx < times.len() - 1 {
        // Advance end_idx until the duration exceeds window_size
        while end_idx < times.len() - 1 && times[end_idx] - times[start_idx] <= window_size {
            end_idx += 1;
        }
        let count = end_idx - start_idx;
        max_count = max_count.max(count);
        //println!("start_idx {start_idx}, end_idx {end_idx}, delta is {} minutes, count {count}", (times[end_idx] - times[start_idx]).num_minutes());

        start_idx += 1;
    }

    max_count
}
