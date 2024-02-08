use anyhow::Result;
use chrono::{Duration, NaiveTime};
use fs_err::File;
use geojson::{Feature, Geometry, Value};

mod gtfs;

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    if args.len() != 2 {
        panic!("Call with the path to the unzipped GTFS directory");
    }

    let stops = gtfs::get_stops(&args[1])?;

    println!("Finding peaks");
    let mut writer = geojson::FeatureWriter::from_writer(std::io::BufWriter::new(File::create(
        "stops.geojson",
    )?));
    for (stop_id, stop) in stops {
        // For each day, calculate the total stops that day and the peak
        let mut max_total_stops = 0;
        let mut max_peak = 0;
        for times in stop.times_per_day {
            if times.is_empty() {
                continue;
            }

            let total_stops = times.len();
            let peak = sliding_window_peak(times, Duration::hours(1));
            max_total_stops = max_total_stops.max(total_stops);
            max_peak = max_peak.max(peak);
        }

        let mut f = Feature::from(Geometry::new(Value::Point(vec![stop.lon, stop.lat])));
        f.set_property("stop_id", stop_id);
        f.set_property("stop_name", stop.name);
        f.set_property("total_stops", max_total_stops);
        f.set_property("peak", max_peak);
        writer.write_feature(&f)?;
    }

    Ok(())
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
