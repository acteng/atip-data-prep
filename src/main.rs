use abstutil::Timer;
use map_model::osm::RoadRank;
use map_model::{Map, Perimeter};

fn main() {
    let map_filename = std::env::args().nth(1).expect("no map filename provided");
    let area_filename = std::env::args().nth(2).expect("no area filename provided");
    let mut timer = Timer::new("convert");

    // TODO Map::load_synchronously expects the data/ directory to exist
    let map: Map = abstio::maybe_read_binary(map_filename, &mut timer).unwrap();
    map_to_areas(&map, area_filename, &mut timer);
}

// Logic adapted from LTN partition.rs and the test crate
fn map_to_areas(map: &Map, out_filename: String, timer: &mut Timer) {
    timer.start(format!("map_to_areas for {}", map.get_name().describe()));

    timer.start("find_all_single_blocks and partition");
    let mut single_block_perims = Vec::new();
    let input = Perimeter::merge_holes(map, Perimeter::find_all_single_blocks(map));
    for mut perim in input {
        perim.collapse_deadends();
        if let Ok(block) = perim.to_block(map) {
            single_block_perims.push(block.perimeter);
        }
    }

    let partitions = Perimeter::partition_by_predicate(single_block_perims, |r| {
        map.get_r(r).get_rank() == RoadRank::Local
    });
    timer.stop("find_all_single_blocks and partition");

    timer.start_iter("merge", partitions.len());
    let mut merged = Vec::new();
    for perimeters in partitions {
        timer.next();
        let stepwise_debug = false;
        let use_expensive_blockfinding = false;
        merged.extend(Perimeter::merge_all(
            map,
            perimeters,
            stepwise_debug,
            use_expensive_blockfinding,
        ));
    }

    timer.start_iter("blockify", merged.len());
    let mut blocks = Vec::new();
    for perimeter in merged {
        timer.next();
        if let Ok(block) = perimeter.to_block(map) {
            blocks.push(block);
        }
    }

    let mut pairs = Vec::new();
    for block in blocks {
        let props = serde_json::Map::new();
        pairs.push((block.polygon.to_geojson(Some(map.get_gps_bounds())), props));
    }
    abstio::write_json(
        out_filename,
        &geom::geometries_with_properties_to_geojson(pairs),
    );

    timer.stop(format!("map_to_areas for {}", map.get_name().describe()));
}
