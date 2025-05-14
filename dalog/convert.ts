import * as fs from "fs";
import { execSync } from "child_process";
import readXlsxFile from "read-excel-file/node";
import type { FeatureCollection } from "geojson";

async function main() {
  let gj: FeatureCollection = {
    type: "FeatureCollection",
    features: [],
  };

  let file = fs.readFileSync(process.argv[2]);

  // The automatic column detection doesn't work, because there's an empty row and column at the start
  let rows = await readXlsxFile(file, {
    sheet: "Issues",
  });
  let keys = rows[1].slice(1);
  for (let row of rows.slice(2)) {
    let obj = Object.fromEntries(keys.map((key, i) => [key, row[i + 1]]));
    if (obj["Issue ID"] == null) {
      continue;
    }

    let ll = obj["Latitude & Longitude"];
    if (ll == 0 || ll == null || ll == undefined) {
      // TODO Only one case
      console.warn(`No coordinates, skipping entry`);
      console.warn(obj);
      continue;
    }
    let coordinates = ll.split(", ").map(parseFloat).reverse();

    delete obj["Latitude & Longitude"];
    delete obj["Google Maps"];
    delete obj["Cumul. Type"];
    delete obj["Proposed ID"];

    gj.features.push({
      type: "Feature",
      properties: obj,
      geometry: {
        type: "Point",
        coordinates,
      },
      id: gj.features.length + 1,
    });
  }

  fs.writeFileSync("problems.geojson", JSON.stringify(gj));
  fs.unlinkSync("problems.geojson.gz");
  execSync("gzip problems.geojson");
  console.log("problems.geojson.gz is ready");
}

main();
