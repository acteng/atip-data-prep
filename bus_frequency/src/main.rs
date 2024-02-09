use anyhow::Result;
use chrono::{Duration, NaiveTime};
use fs_err::File;
use geojson::{Feature, Geometry, Value};

use self::gtfs::Day;

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
    let days = vec![
        Day::Monday,
        Day::Tuesday,
        Day::Wednesday,
        Day::Thursday,
        Day::Friday,
        Day::Saturday,
        Day::Sunday,
    ];
    for (stop_id, stop) in stops {
        // For each day, calculate the total buses that day and during the peak hour
        let mut per_day: Vec<(Day, usize, usize, String)> = Vec::new();
        for (idx, times) in stop.times_per_day.into_iter().enumerate() {
            let total = times.len();
            let (peak, interval) = sliding_window_peak(times, Duration::hours(1));
            let describe_interval = match interval {
                Some((t1, t2)) => format!("{t1} - {t2} on {:?}", days[idx]),
                None => "no buses".to_string(),
            };
            per_day.push((days[idx], total, peak, describe_interval));
        }

        let max_total = per_day.iter().max_by_key(|tuple| tuple.1).unwrap();
        let max_peak = per_day.iter().max_by_key(|tuple| tuple.2).unwrap();

        let mut f = Feature::from(Geometry::new(Value::Point(vec![stop.lon, stop.lat])));
        f.set_property("stop_id", stop_id);
        f.set_property("stop_name", stop.name);
        f.set_property("total", max_total.1);
        f.set_property("total_description", format!("{:?}", max_total.0));
        f.set_property("peak", max_peak.2);
        f.set_property("peak_description", max_peak.3.clone());
        writer.write_feature(&f)?;
    }

    Ok(())
}

/// Finds the interval of length `window_size` containing the most `times`. Returns that interval
/// (unless it's empty) and th number of `times` in it
fn sliding_window_peak(
    mut times: Vec<NaiveTime>,
    window_size: Duration,
) -> (usize, Option<(NaiveTime, NaiveTime)>) {
    times.sort();

    if times.is_empty() {
        return (0, None);
    }
    if times.len() == 1 {
        return (1, Some((times[0], times[0] + window_size)));
    }

    let mut start_idx = 0;
    let mut end_idx = 0;
    let mut max_count = 0;
    let mut start_time_of_max = times[0];

    while start_idx < times.len() - 1 {
        // Advance end_idx until the duration exceeds window_size
        while end_idx < times.len() - 1 && times[end_idx] - times[start_idx] <= window_size {
            end_idx += 1;
        }
        let count = end_idx - start_idx;
        if count > max_count {
            max_count = count;
            start_time_of_max = times[start_idx];
        }
        //println!("start_idx {start_idx}, end_idx {end_idx}, delta is {} minutes, count {count}", (times[end_idx] - times[start_idx]).num_minutes());

        start_idx += 1;
    }

    (
        max_count,
        Some((start_time_of_max, start_time_of_max + window_size)),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn time(t: &str) -> NaiveTime {
        NaiveTime::parse_from_str(t, "%H:%M:%S").unwrap()
    }

    #[test]
    fn test_sliding_window_peak() {
        for (input, expected_peak, expected_interval) in vec![
            // Degenerate cases
            (vec![], 0, None),
            (vec!["07:13:00"], 1, Some(("07:13:00", "08:13:00"))),
            (
                vec!["07:13:00", "09:05:00"],
                1,
                Some(("07:13:00", "08:13:00")),
            ),
            (
                vec![
                    "05:00:00", "07:05:00", "07:10:00", "07:15:00", "07:20:00", "08:30:00",
                    "08:45:00",
                ],
                4,
                Some(("07:05:00", "08:05:00")),
            ),
            (
                vec![
                    "05:00:00", "06:35:00", "07:10:00", "07:15:00", "07:20:00", "08:30:00",
                    "08:45:00",
                ],
                4,
                Some(("06:35:00", "07:35:00")),
            ),
        ] {
            let times: Vec<NaiveTime> = input.into_iter().map(time).collect();
            let (actual_peak, actual_interval) = sliding_window_peak(times, Duration::hours(1));

            assert_eq!(expected_peak, actual_peak);
            assert_eq!(
                expected_interval.map(|(t1, t2)| (time(t1), time(t2))),
                actual_interval
            );
        }
    }
}
