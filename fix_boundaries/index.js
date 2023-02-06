import convex from "@turf/convex";
import * as fs from "fs";

let gj = JSON.parse(fs.readFileSync("../authorities.geojson"));
for (let feature of gj.features) {
  if (feature.geometry.type != "MultiPolygon") {
    continue;
  }
  feature.geometry = convex(feature).geometry;

  // Convenient debugging
  /*if (feature.properties.name == "Portsmouth") {
    fs.writeFileSync("debug.geojson", JSON.stringify(feature));
  }*/
}
fs.writeFileSync("../authorities.geojson", JSON.stringify(gj));
