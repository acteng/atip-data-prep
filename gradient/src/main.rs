use std::cell::RefCell;
use std::collections::HashMap;
use std::io::{BufReader, BufWriter};

use anyhow::Result;
use elevation::GeoTiffElevation;
use fs_err::File;
use geo::{Coord, HaversineLength, LineString};
use geojson::{Feature, FeatureWriter, Geometry};
use indicatif::{ParallelProgressIterator, ProgressBar, ProgressStyle};
use osm_reader::{Element, NodeID, WayID};
use rayon::prelude::*;

/// This takes an osm.pbf file and a GeoTIFF file covering the area. The GeoTIFF must be a digital
/// elevation model in WGS84 and units of meters. The output is a GeoJSON file with LineStrings for
/// every way, with a `gradient` property.
///
/// Gradient is:
///
/// - positive when the edge is uphill from start to end based on the LineString order, and
///   negative when downhill
/// - expressed as an integer percent multiplied by 100 -- a value of `305` means a `3.05%` grade.
fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        panic!("Call with the input path to an osm.pbf and a GeoTIFF file");
    }

    run(&args[1], &args[2], "tmp/gradient.geojson").unwrap();
}

fn run(osm_path: &str, tif_path: &str, output_path: &str) -> Result<()> {
    let edges = scrape_osm(osm_path)?;

    println!("Calculating gradient");
    let progress = ProgressBar::new(edges.len() as u64).with_style(ProgressStyle::with_template(
        "[{elapsed_precise}] [{wide_bar:.cyan/blue}] {human_pos}/{human_len} ({per_sec}, {eta})").unwrap());
    // Calculate gradient in parallel.
    let gradients: Vec<(LineString, isize)> = edges
        .into_par_iter()
        .progress_with(progress)
        .map(|(_, linestring)| {
            // The geotiff reader can only be used from one thread, so open the file about once per
            // thread (based on how rayon decides to split the work).
            thread_local!(static ELEVATION: RefCell<Option<GeoTiffElevation<BufReader<File>>>> = RefCell::new(None));
            ELEVATION.with(|elevation_cell| {
                let mut elevation = elevation_cell.borrow_mut();
                if elevation.is_none() {
                    *elevation = Some(GeoTiffElevation::new(BufReader::new(File::open(tif_path).unwrap())));
                }

                let gradient = get_steepness(&linestring, elevation.as_mut().unwrap());
                (linestring, gradient)
            })
        })
        .collect();

    println!("Writing output");
    let progress = ProgressBar::new(gradients.len() as u64).with_style(ProgressStyle::with_template(
        "[{elapsed_precise}] [{wide_bar:.cyan/blue}] {human_pos}/{human_len} ({per_sec}, {eta})").unwrap());
    let mut out = FeatureWriter::from_writer(BufWriter::new(File::create(output_path)?));
    for (linestring, gradient) in gradients {
        progress.inc(1);
        let mut f = Feature::from(Geometry::from(&linestring));
        f.set_property("gradient", gradient);
        out.write_feature(&f)?;
    }
    progress.finish();

    Ok(())
}

fn scrape_osm(osm_path: &str) -> Result<Vec<(WayID, LineString)>> {
    let mut node_mapping: HashMap<NodeID, Coord> = HashMap::new();
    let mut highways: Vec<(WayID, Vec<NodeID>)> = Vec::new();
    let mut first_way = true;
    println!("Reading {osm_path}");
    let nodes_progress = ProgressBar::new_spinner().with_style(
        ProgressStyle::with_template("[{elapsed_precise}] {human_len} nodes read ({per_sec})")
            .unwrap(),
    );
    let ways_progress = ProgressBar::new_spinner().with_style(
        ProgressStyle::with_template("[{elapsed_precise}] {human_len} ways read ({per_sec})")
            .unwrap(),
    );
    osm_reader::parse(&fs_err::read(osm_path)?, |elem| match elem {
        Element::Node { id, lon, lat, .. } => {
            nodes_progress.inc(1);
            node_mapping.insert(id, Coord { x: lon, y: lat });
        }
        Element::Way { id, node_ids, tags } => {
            if tags.contains_key("highway") && tags.get("area") != Some(&"yes".to_string()) {
                if first_way {
                    nodes_progress.finish();
                    first_way = false;
                }
                ways_progress.inc(1);
                highways.push((id, node_ids));
            }
        }
        Element::Relation { .. } | Element::Bounds { .. } => {}
    })?;
    ways_progress.finish();

    Ok(split_edges(node_mapping, highways))
}

fn split_edges(
    node_mapping: HashMap<NodeID, Coord>,
    ways: Vec<(WayID, Vec<NodeID>)>,
) -> Vec<(WayID, LineString)> {
    println!("Splitting ways into edges");

    // Count how many ways reference each node
    let mut node_counter: HashMap<NodeID, usize> = HashMap::new();
    for (_, node_ids) in &ways {
        for node in node_ids {
            *node_counter.entry(*node).or_insert(0) += 1;
        }
    }

    // Split each way into edges
    let progress = ProgressBar::new(ways.len() as u64).with_style(ProgressStyle::with_template(
        "[{elapsed_precise}] [{wide_bar:.cyan/blue}] {human_pos}/{human_len} ({per_sec}, {eta})").unwrap());
    let mut edges = Vec::new();
    for (way_id, node_ids) in ways {
        progress.inc(1);
        let mut pts = Vec::new();

        let num_nodes = node_ids.len();
        for (idx, node) in node_ids.into_iter().enumerate() {
            pts.push(node_mapping[&node]);
            // Edges start/end at intersections between two ways. The endpoints of the way also
            // count as intersections.
            let is_endpoint =
                idx == 0 || idx == num_nodes - 1 || *node_counter.get(&node).unwrap() > 1;
            if is_endpoint && pts.len() > 1 {
                edges.push((way_id, LineString::new(std::mem::take(&mut pts))));

                // Start the next edge
                pts.push(node_mapping[&node]);
            }
        }
    }
    progress.finish();
    edges
}

fn get_steepness(edge: &LineString, elevation: &mut GeoTiffElevation<BufReader<File>>) -> isize {
    // Calculate height at the endpoints. Ignore anything in the middle -- if a long edge has a
    // hill or valley in the middle, we'll ignore it.
    let pt1 = edge.points().next().unwrap();
    let height1 = elevation
        .get_height_for_lon_lat(pt1.x() as f32, pt1.y() as f32)
        .unwrap();
    let pt2 = edge.points().last().unwrap();
    let height2 = elevation
        .get_height_for_lon_lat(pt2.x() as f32, pt2.y() as f32)
        .unwrap();

    let length = edge.haversine_length() as f32;
    let gradient = (height2 - height1) / length;
    (gradient * 10_000.0) as isize
}
