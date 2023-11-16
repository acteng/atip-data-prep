const { readFileSync, writeFileSync } = require("fs");

const allSchemes =  JSON.parse(readFileSync("./data/input/all_scheme_data.geojson"));

const resultingSchemeDictionary = {};
Object.keys(allSchemes.schemes).forEach((browseSchemeKey) => {
    const scheme = allSchemes.schemes[browseSchemeKey];
    const result = {
        scheme_name: browseSchemeKey,
        scheme_reference: browseSchemeKey,
        browse: scheme
    }
    resultingSchemeDictionary[browseSchemeKey] = result;
});

allSchemes.schemes = resultingSchemeDictionary;
const outputPath = "./data/output/all_scheme_data.geojson"; 

try {
    writeFileSync(outputPath, JSON.stringify(allSchemes));
    console.log(`Data successfully output to ${outputPath}`)

} catch (error) {
    console.log(`Error writing new all schemes geojson: ${error}`)
}