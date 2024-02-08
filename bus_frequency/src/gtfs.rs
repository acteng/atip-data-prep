use std::collections::BTreeMap;

use anyhow::Result;
use chrono::NaiveTime;
use fs_err::File;
use serde::Deserialize;

pub struct Stop {
    pub name: String,
    pub lon: f64,
    pub lat: f64,

    // Indexed by Day
    pub times_per_day: Vec<Vec<NaiveTime>>,
}

#[derive(Clone, Copy)]
enum Day {
    Monday = 0,
    Tuesday = 1,
    Wednesday = 2,
    Thursday = 3,
    Friday = 4,
    Saturday = 5,
    Sunday = 6,
}

/// Takes a path to a GTFS directory, and returns stop ID mapped to a Stop
pub fn get_stops(dir_path: &str) -> Result<BTreeMap<String, Stop>> {
    println!("Scraping trips.txt");
    let mut trip_to_service = BTreeMap::new();
    for rec in csv::Reader::from_reader(File::open(format!("{dir_path}/trips.txt"))?).deserialize()
    {
        let rec: TripRow = rec?;
        trip_to_service.insert(rec.trip_id, rec.service_id);
    }

    println!("Scraping calendar.txt");
    let mut service_to_days: BTreeMap<String, Vec<Day>> = BTreeMap::new();
    for rec in
        csv::Reader::from_reader(File::open(format!("{dir_path}/calendar.txt"))?).deserialize()
    {
        let rec: CalendarRow = rec?;
        let mut days = Vec::new();
        for (day, include) in [
            (Day::Monday, rec.monday),
            (Day::Tuesday, rec.tuesday),
            (Day::Wednesday, rec.wednesday),
            (Day::Thursday, rec.thursday),
            (Day::Friday, rec.friday),
            (Day::Saturday, rec.saturday),
            (Day::Sunday, rec.sunday),
        ] {
            if include == 1 {
                days.push(day);
            }
        }
        service_to_days.insert(rec.service_id, days);
    }

    println!("Scraping stops.txt");
    let mut stops: BTreeMap<String, Stop> = BTreeMap::new();
    for rec in csv::Reader::from_reader(File::open(format!("{dir_path}/stops.txt"))?).deserialize()
    {
        let rec: StopRow = rec?;
        stops.insert(
            rec.stop_id,
            Stop {
                name: rec.stop_name,
                lon: rec.stop_lon,
                lat: rec.stop_lat,
                times_per_day: std::iter::repeat_with(Vec::new).take(7).collect(),
            },
        );
    }

    println!("Scraping stop_times.txt");
    let mut scraped = 0;
    let mut skipped = 0;
    for rec in
        csv::Reader::from_reader(File::open(format!("{dir_path}/stop_times.txt"))?).deserialize()
    {
        let rec: StopTimeRow = rec?;
        let Ok(arrival_time) = NaiveTime::parse_from_str(&rec.arrival_time, "%H:%M:%S") else {
            // TODO Handle times > 24 hours, or just ignore, since that's very unlikely to be the
            // peak
            //println!("Weird arrival_time {}", rec.arrival_time);
            skipped += 1;
            continue;
        };

        // Which days does this stop occur on?
        let stop = stops.get_mut(&rec.stop_id).unwrap();
        let service = &trip_to_service[&rec.trip_id];
        let Some(days) = service_to_days.get(service) else {
            println!("Don't know what days service {service} is on");
            skipped += 1;
            continue;
        };
        for day in days {
            stop.times_per_day[*day as usize].push(arrival_time);
        }

        scraped += 1;
    }
    println!("Got {scraped} times, skipped {skipped}");

    Ok(stops)
}

#[derive(Deserialize)]
struct TripRow {
    trip_id: String,
    service_id: String,
}

#[derive(Deserialize)]
struct CalendarRow {
    service_id: String,
    monday: usize,
    tuesday: usize,
    wednesday: usize,
    thursday: usize,
    friday: usize,
    saturday: usize,
    sunday: usize,
}

#[derive(Deserialize)]
struct StopRow {
    stop_id: String,
    stop_name: String,
    stop_lon: f64,
    stop_lat: f64,
}

#[derive(Deserialize)]
struct StopTimeRow {
    trip_id: String,
    stop_id: String,
    arrival_time: String,
}
