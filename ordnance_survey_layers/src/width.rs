use anyhow::Result;

pub fn road_width_properties(
    input: &gdal::vector::Feature,
    output: &mut geojson::Feature,
) -> Result<bool> {
    let average = input.field_as_double_by_name("roadwidth_average")?;
    let minimum = input.field_as_double_by_name("roadwidth_minimum")?;

    if let (Some(average), Some(minimum)) = (average, minimum) {
        output.set_property("average", average);
        output.set_property("minimum", minimum);
        Ok(true)
    } else {
        // Exclude missing data
        Ok(false)
    }
}

pub fn pavement_width_properties(
    input: &gdal::vector::Feature,
    output: &mut geojson::Feature,
) -> Result<bool> {
    let average = input.field_as_double_by_name("presenceofpavement_averagewidth_m")?;
    let minimum = input.field_as_double_by_name("presenceofpavement_minimumwidth_m")?;
    let side = input.field_as_string_by_name("presenceofpavement_sideofroad")?;

    if let (Some(average), Some(minimum), Some(side)) = (average, minimum, side) {
        // If they're both 0, don't show anything
        if average == 0.0 && minimum == 0.0 {
            return Ok(false);
        }

        output.set_property("side", side);
        output.set_property("average", average);
        output.set_property("minimum", minimum);
        Ok(true)
    } else {
        // Exclude missing data
        Ok(false)
    }
}
