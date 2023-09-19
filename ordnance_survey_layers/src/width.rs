use anyhow::Result;

pub fn width_properties(
    input: &gdal::vector::Feature,
    output: &mut geojson::Feature,
) -> Result<bool> {
    let average = input.field_as_integer_by_name("roadwidth_average")?;
    let minimum = input.field_as_integer_by_name("roadwidth_minimum")?;

    if let (Some(average), Some(minimum)) = (average, minimum) {
        output.set_property("average", average);
        output.set_property("minimum", minimum);
        Ok(true)
    } else {
        // Exclude missing data
        Ok(false)
    }
}
