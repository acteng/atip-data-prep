use std::collections::HashMap;
use std::fs::File;
use std::io::BufWriter;

use anyhow::Result;
use geo::{Coord, LineString, Point};
use geojson::{Feature, FeatureWriter, Geometry};
use osm_reader::{Element, NodeID, WayID};
use serde::Serialize;
use utils::Tags;

struct Node {
    id: NodeID,
    pt: Coord,
    tags: Tags,
}

struct Way {
    id: WayID,
    linestring: LineString,
    tags: Tags,
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    let input_bytes = std::fs::read(&args[1])?;

    println!("Parsing {} bytes of OSM data", input_bytes.len());
    let mut nodes = HashMap::new();
    let mut ways = Vec::new();

    osm_reader::parse(&input_bytes, |elem| match elem {
        Element::Node {
            id, lon, lat, tags, ..
        } => {
            let pt = Coord { x: lon, y: lat };
            let tags: Tags = tags.into();
            // Keep all nodes, because ways might reference them
            nodes.insert(id, Node { id, pt, tags });
        }
        Element::Way {
            id, node_ids, tags, ..
        } => {
            let tags: Tags = tags.into();
            let linestring = LineString(node_ids.iter().map(|n| nodes[n].pt).collect());

            // Only keep interesting ways
            if tags.is_any_key(vec!["highway", "footway", "cycleway"], "crossing")
                || tags.is("footway", "traffic_island")
            {
                ways.push(Way {
                    id,
                    linestring,
                    tags,
                });
            }
        }
        // Ignore relations
        _ => {}
    })?;

    println!("Done parsing, now writing output");
    let mut out = FeatureWriter::from_writer(BufWriter::new(File::create("crossings.geojson")?));
    for way in ways {
        let mut f = Feature::from(Geometry::from(&way.linestring));
        f.set_property("osm", format!("way/{}", way.id.0));
        f.set_property("class", serde_json::to_value(classify(&way.tags))?);
        out.write_feature(&f)?;
    }

    for (_, node) in nodes {
        if !node
            .tags
            .is_any_key(vec!["highway", "footway", "cycleway"], "crossing")
        {
            continue;
        }
        let mut f = Feature::from(Geometry::from(&Point::from(node.pt)));
        f.set_property("osm", format!("node/{}", node.id.0));
        f.set_property("class", serde_json::to_value(classify(&node.tags))?);
        out.write_feature(&f)?;
    }

    Ok(())
}

#[derive(Serialize)]
enum Crossing {
    Zebra,
    Parallel,
    Pelican,
    Puffin,
    Toucan,
    Pegasus,
    Uncontrolled,
    Signalised,
}

fn classify(tags: &Tags) -> Option<Crossing> {
    // See https://wiki.openstreetmap.org/wiki/Key:crossing_ref#United_Kingdom
    if let Some(x) = tags.get("crossing_ref") {
        return match x.as_str() {
            "zebra" => Some(Crossing::Zebra),
            "tiger" | "parallel" => Some(Crossing::Parallel),
            "pelican" => Some(Crossing::Pelican),
            "puffin" => Some(Crossing::Puffin),
            "toucan" => Some(Crossing::Toucan),
            "pegasus" => Some(Crossing::Pegasus),
            // TODO What're these?
            _ => None,
        };
    }

    if let Some(x) = tags.get("crossing") {
        return match x.as_str() {
            // Careful with the OSM terminology here, see
            // https://wiki.openstreetmap.org/wiki/Tag:crossing%3Dunmarked
            "unmarked" => Some(Crossing::Uncontrolled),
            "zebra" => Some(Crossing::Zebra),
            "traffic_signals" => Some(Crossing::Signalised),
            _ => None,
        };
    }

    None
}
