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
        // For each day, calculate the total buses that day and during the peak hour
        let mut max_total = 0;
        let mut max_peak = 0;
        for times in stop.times_per_day {
            let total = times.len();
            let peak = sliding_window_peak(times, Duration::hours(1));
            max_total = max_total.max(total);
            max_peak = max_peak.max(peak);
        }

        let mut f = Feature::from(Geometry::new(Value::Point(vec![stop.lon, stop.lat])));
        f.set_property("stop_id", stop_id);
        f.set_property("stop_name", stop.name);
        f.set_property("total", max_total);
        f.set_property("peak", max_peak);
        writer.write_feature(&f)?;
    }

    Ok(())
}

/// Finds the interval of length `window_size` containing the most `times`, and returns that number
fn sliding_window_peak(mut times: Vec<NaiveTime>, window_size: Duration) -> usize {
    times.sort();

    if times.is_empty() {
        return 0;
    }
    if times.len() == 1 {
        return 1;
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sliding_window_peak() {
        for (expected_peak, times) in vec![
            // Degenerate cases
            (0, vec![]),
            (1, vec!["07:13:00"]),
            (1, vec!["07:13:00", "09:05:00"]),
            // Lined up on the hour, 7-8 being the peak
            (
                4,
                vec![
                    "05:00:00", "07:05:00", "07:10:00", "07:15:00", "07:20:00", "08:30:00",
                    "08:45:00",
                ],
            ),
            // 6:35 - 7:35 is the peak
            (
                4,
                vec![
                    "05:00:00", "06:35:00", "07:10:00", "07:15:00", "07:20:00", "08:30:00",
                    "08:45:00",
                ],
            ),
        ] {
            let input: Vec<NaiveTime> = times
                .into_iter()
                .map(|t| NaiveTime::parse_from_str(t, "%H:%M:%S").unwrap())
                .collect();
            assert_eq!(
                expected_peak,
                sliding_window_peak(input, Duration::hours(1))
            );
        }
    }
}
