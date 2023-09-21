use anyhow::Result;

pub fn speed_properties(
    input: &gdal::vector::Feature,
    output: &mut geojson::Feature,
) -> Result<bool> {
    let (highest_mph, highest_description) = highest_speed(input)?;
    let indicative_mph = input
        .field_as_integer_by_name("indicativespeedlimit_mph")?
        .unwrap();

    output.set_property("indicative_mph", indicative_mph);
    output.set_property("highest_mph", highest_mph);
    output.set_property("highest_description", highest_description);
    Ok(true)
}

fn highest_speed(feature: &gdal::vector::Feature) -> Result<(usize, &'static str)> {
    let mut max_kph = None;
    let mut max_key = None;
    for time in [
        "mf4to7", "mf7to9", "mf9to12", "mf12to14", "mf14to16", "mf16to19", "mf19to22", "mf22to4",
        "ss4to7", "ss7to10", "ss10to14", "ss14to19", "ss19to22", "ss22to4",
    ] {
        for direction in ["indirection", "againstdirection"] {
            let key = format!("averagespeed_{time}{direction}_kph");
            // TODO Field indices might be faster?
            if let Some(value) = feature.field_as_double_by_name(&key)? {
                // TODO value of 0.0 means unknown error?
                if max_kph.map(|n| n < value).unwrap_or(true) {
                    max_kph = Some(value);
                    max_key = Some(time);
                }
            }
        }
    }

    Ok((
        kph_to_mph(max_kph.unwrap()).round() as usize,
        max_key.unwrap(),
    ))
}

fn kph_to_mph(x: f64) -> f64 {
    x / 1.6
}
