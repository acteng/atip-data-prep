use std::collections::HashMap;

use geom::{Distance, GPSBounds, PolyLine, Pt2D};
use osm2streets::StreetNetwork;
use serde::{Deserialize, Serialize};

// The minimal state needed for a web route-snapping tool. Just a graph of roads and intersections,
// really.
#[derive(Serialize, Deserialize)]
pub struct RouteSnapperMap {
    pub gps_bounds: GPSBounds,
    pub intersections: Vec<Pt2D>,
    pub roads: Vec<Road>,
    pub road_lookup: HashMap<(IntersectionID, IntersectionID), RoadID>,
}

#[derive(Serialize, Deserialize)]
pub struct Road {
    pub i1: IntersectionID,
    pub i2: IntersectionID,
    pub center_pts: PolyLine,
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
            road_lookup: HashMap::new(),
        };

        let mut id_lookup = HashMap::new();
        for (id, i) in &streets.intersections {
            map.intersections.push(i.point);
            id_lookup.insert(*id, IntersectionID(id_lookup.len()));
        }
        for (id, r) in &streets.roads {
            let i1 = id_lookup[&id.i1];
            let i2 = id_lookup[&id.i2];
            map.road_lookup.insert((i1, i2), RoadID(map.roads.len()));
            let center_pts = PolyLine::unchecked_new(r.osm_center_points.clone());
            map.roads.push(Road {
                i1,
                i2,
                length: center_pts.length(),
                center_pts,
            });
        }

        map
    }
}
