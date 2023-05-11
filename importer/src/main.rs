use std::fs::File;
use std::io::BufWriter;

use abstutil::Timer;
use anyhow::Result;
use geom::LonLat;
use osm2streets::{MapConfig, Transformation};

/// Takes a .osm and a .geojson of the boundary, imports with osm2streets, and writes a bincoded
/// StreetNetwork file to out.bin
fn main() -> Result<()> {
    // Leave this disabled to run more quickly, but enable for debugging
    //abstutil::logger::setup();
    let args: Vec<String> = std::env::args().collect();
    assert_eq!(
        args.len(),
        4,
        "Call with a .osm input, a .geojson boundary, and a .bin output"
    );
    let osm_input = &args[1];
    let geojson_input = &args[2];
    let output = &args[3];

    let mut timer = Timer::new("import map");
    let clip_pts = Some(LonLat::read_geojson_polygon(geojson_input)?);
    let (mut street_network, _) = streets_reader::osm_to_street_network(
        &std::fs::read_to_string(osm_input)?,
        clip_pts,
        MapConfig::default(),
        &mut timer,
    )?;
    street_network.apply_transformations(Transformation::standard_for_clipped_areas(), &mut timer);

    let file = BufWriter::new(File::create(output)?);
    bincode::serialize_into(file, &street_network)?;

    Ok(())
}
