use std::collections::HashMap;

use geom::{Distance, GPSBounds, Pt2D};
use osm2streets::StreetNetwork;
use petgraph::graphmap::UnGraphMap;
use serde::{Deserialize, Serialize};

// The minimal state needed for a web route-snapping tool. Just a graph of roads and intersections,
// really.
#[derive(Serialize, Deserialize)]
pub struct RouteSnapperMap {
    pub gps_bounds: GPSBounds,
    pub intersections: Vec<Pt2D>,
    pub roads: Vec<Road>,
}

#[derive(Serialize, Deserialize)]
pub struct Road {
    pub i1: IntersectionID,
    pub i2: IntersectionID,
    pub pts: Vec<Pt2D>,
    pub length: Distance,
}

#[derive(Serialize, Deserialize, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct RoadID(usize);
#[derive(Serialize, Deserialize, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct IntersectionID(usize);

impl RouteSnapperMap {
    pub fn new(streets: &StreetNetwork) -> Self {
        let mut map = Self {
            gps_bounds: streets.gps_bounds.clone(),
            intersections: Vec::new(),
            roads: Vec::new(),
        };

        let mut id_lookup = HashMap::new();
        for (id, i) in &streets.intersections {
            map.intersections.push(i.point);
            id_lookup.insert(*id, IntersectionID(id_lookup.len()));
        }
        for (id, r) in &streets.roads {
            map.roads.push(Road {
                i1: id_lookup[&id.i1],
                i2: id_lookup[&id.i2],
                pts: r.osm_center_points.clone(),
                length: r.length(),
            });
        }

        map
    }

    pub fn pathfind(
        &self,
        i1: IntersectionID,
        i2: IntersectionID,
    ) -> Option<(Vec<RoadID>, Vec<IntersectionID>)> {
        let mut graph: UnGraphMap<IntersectionID, RoadID> = UnGraphMap::new();
        for (idx, r) in self.roads.iter().enumerate() {
            graph.add_edge(r.i1, r.i2, RoadID(idx));
        }
        let (_, path) = petgraph::algo::astar(
            &graph,
            i1,
            |i| i == i2,
            |(_, _, r)| self.roads[r.0].length,
            |_| Distance::ZERO,
        )?;
        let roads: Vec<RoadID> = path
            .windows(2)
            .map(|pair| *graph.edge_weight(pair[0], pair[1]).unwrap())
            .collect();
        Some((roads, path))
    }
}
