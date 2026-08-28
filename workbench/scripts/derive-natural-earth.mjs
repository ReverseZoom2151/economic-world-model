import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import process from "node:process";

const EXPECTED_SOURCE_DIGEST = "6866c877d39cba9c357620878839b336d569f8c662d3cfab4cb1dbe2d39c977f";

const [inputPath, outputPath] = process.argv.slice(2);
if (inputPath === undefined || outputPath === undefined) {
  throw new Error("usage: node scripts/derive-natural-earth.mjs INPUT OUTPUT");
}

const source = await readFile(inputPath);
const digest = createHash("sha256").update(source).digest("hex");
if (digest !== EXPECTED_SOURCE_DIGEST) {
  throw new Error(`Natural Earth source digest mismatch: ${digest}`);
}

const collection = JSON.parse(source.toString("utf8"));
if (collection.type !== "FeatureCollection" || !Array.isArray(collection.features)) {
  throw new Error("Natural Earth source is not a GeoJSON FeatureCollection");
}

const derived = {
  type: "FeatureCollection",
  features: collection.features.map((feature) => ({
    type: "Feature",
    id: feature.id ?? null,
    properties: {
      name: feature.properties?.NAME ?? null,
      adm0_a3: feature.properties?.ADM0_A3 ?? null,
    },
    geometry: feature.geometry,
  })),
};

await writeFile(outputPath, `${JSON.stringify(derived)}\n`, "utf8");
