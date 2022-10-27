use geom::{GPSBounds, Pt2D};
use osm2streets::StreetNetwork;
use serde::{Deserialize, Serialize};

// The minimal state needed for a web route-snapping tool. Just a graph of roads and intersections,
// really.
#[derive(Serialize, Deserialize)]
pub struct RouteSnapperMap {
    gps_bounds: GPSBounds,
    intersections: Vec<Pt2D>,
    roads: Vec<Vec<Pt2D>>,
    // TODO Enough graph structure to do pathfinding
}

struct RoadID(usize);
struct IntersectionID(usize);

impl RouteSnapperMap {
    pub fn new(streets: &StreetNetwork) -> Self {
        let mut map = Self {
            gps_bounds: streets.gps_bounds.clone(),
            intersections: Vec::new(),
            roads: Vec::new(),
        };

        for i in streets.intersections.values() {
            map.intersections.push(i.point);
        }
        for r in streets.roads.values() {
            map.roads.push(r.osm_center_points.clone());
        }

        map
    }
}
