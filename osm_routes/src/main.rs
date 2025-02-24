use std::collections::HashMap;
use std::fs::File;
use std::io::BufWriter;

use anyhow::Result;
use geo::{Coord, LineString, MultiLineString};
use geojson::{Feature, FeatureWriter, Geometry};
use osm_reader::{Element, NodeID, OsmID, WayID};

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    let input_bytes = std::fs::read(&args[1])?;

    println!("Parsing {} bytes of OSM data", input_bytes.len());
    let mut nodes: HashMap<NodeID, Coord> = HashMap::new();
    let mut ways: HashMap<WayID, LineString> = HashMap::new();
    let mut out = FeatureWriter::from_writer(BufWriter::new(File::create("cycle_routes.geojson")?));

    osm_reader::parse(&input_bytes, |elem| match elem {
        Element::Node { id, lon, lat, .. } => {
            nodes.insert(id, Coord { x: lon, y: lat });
        }
        Element::Way {
            id, node_ids, tags, ..
        } => {
            if tags.contains_key("highway") || tags.get("cycleway") == Some(&"crossing".to_string())
            {
                ways.insert(id, LineString(node_ids.iter().map(|n| nodes[n]).collect()));
            }
        }
        Element::Relation {
            id, tags, members, ..
        } => {
            if tags.get("route") == Some(&"bicycle".to_string()) {
                if let Some(multi_linestring) = glue_route_linestring(members, &ways) {
                    let mut f = Feature::from(Geometry::from(&multi_linestring));
                    f.set_property("osm_relation", id.0);
                    f.set_property(
                        "name",
                        tags.get("name").cloned().unwrap_or_else(String::new),
                    );
                    out.write_feature(&f).unwrap();
                }
            }
        }
        Element::Bounds { .. } => {}
    })?;

    Ok(())
}

// OSM relations are expressed as a list of members (nodes, ways, or other relations). For routes,
// most of the members are ways representing a contiguous stretch of road. Usually these are listed
// "in order", but sometimes maintaining this is hard. We turn these into a small number of of
// LineStrings, trying to glue things together when they are listed in order. This is best-effort
// and not that important -- ultimately this layer is just used for visualization.
//
// Besides, route relations are not always simple linear objects:
//
// - There might be small roundabouts, like https://www.openstreetmap.org/relation/2649#map=19/52.060536/1.201455
// - There could be a different alignment for each direction of the route, like
// https://www.openstreetmap.org/relation/16732611#map=17/52.965112/-0.028882
//
// Note that multiple routes may cross the same physical roads and thus overlap. For simplicity, we
// ignore "meta" relations that only group other ones, like
// https://www.openstreetmap.org/relation/2696.
fn glue_route_linestring(
    members: Vec<(String, OsmID)>,
    ways: &HashMap<WayID, LineString>,
) -> Option<MultiLineString> {
    let mut pieces: Vec<Vec<Coord>> = Vec::new();

    'MEMBER: for (_, id) in members {
        if let OsmID::Way(way) = id {
            let mut pts = match ways.get(&way) {
                Some(linestring) => linestring.0.clone(),
                None => {
                    // Route relations might reference ways that aren't tagged as a road
                    continue;
                }
            };

            // Is there an existing piece that we can glue to?
            for piece in &mut pieces {
                if piece.first().unwrap() == pts.first().unwrap() {
                    piece.reverse();
                    piece.pop();

                    piece.extend(pts);
                    continue 'MEMBER;
                } else if piece.first().unwrap() == pts.last().unwrap() {
                    piece.reverse();
                    piece.pop();
                    pts.reverse();

                    piece.extend(pts);
                    continue 'MEMBER;
                } else if piece.last().unwrap() == pts.first().unwrap() {
                    piece.pop();

                    piece.extend(pts);
                    continue 'MEMBER;
                } else if piece.last().unwrap() == pts.last().unwrap() {
                    pts.reverse();
                    piece.pop();

                    piece.extend(pts);
                    continue 'MEMBER;
                }
            }

            // Start a new piece
            pieces.push(pts);
        }
    }

    // To handle members listed out of order, we could try a second pass to glue things together,
    // but it's not really that useful to.

    if pieces.is_empty() {
        None
    } else {
        Some(MultiLineString(
            pieces.into_iter().map(LineString).collect(),
        ))
    }
}
