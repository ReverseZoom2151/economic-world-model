import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const workbench = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const project = resolve(workbench, "..");
const output = resolve(workbench, "src", "contracts", "generated.ts");

function pythonExecutable() {
  const configured = process.env.PYTHON;
  if (configured) {
    return configured;
  }
  const candidates = [
    resolve(project, ".venv", "bin", "python"),
    resolve(project, ".venv", "Scripts", "python.exe"),
  ];
  return candidates.find((candidate) => existsSync(candidate)) ?? "python";
}

const generated = spawnSync(
  pythonExecutable(),
  ["-m", "ewm.workbench.contracts"],
  {
    cwd: project,
    encoding: "utf8",
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
  },
);
if (generated.status !== 0) {
  throw new Error(`OpenAPI generation failed: ${generated.stderr.trim()}`);
}

const canonicalOpenApi = generated.stdout.trim();
const document = JSON.parse(canonicalOpenApi);
if (!document.openapi?.startsWith("3.1.") || typeof document.paths !== "object") {
  throw new Error("Python contract generator returned an invalid OpenAPI 3.1 document");
}

const schemas = document.components?.schemas ?? {};

function typeName(reference) {
  return reference.split("/").at(-1);
}

function renderType(schema) {
  if (!schema || Object.keys(schema).length === 0) {
    return "unknown";
  }
  if (schema.$ref) {
    return typeName(schema.$ref);
  }
  if (Object.hasOwn(schema, "const")) {
    return JSON.stringify(schema.const);
  }
  if (schema.enum) {
    return schema.enum.map((value) => JSON.stringify(value)).join(" | ");
  }
  const alternatives = schema.anyOf ?? schema.oneOf;
  if (alternatives) {
    return alternatives.map(renderType).join(" | ");
  }
  if (schema.type === "array") {
    return `ReadonlyArray<${renderType(schema.items)}>`;
  }
  if (schema.type === "object" || schema.properties) {
    const required = new Set(schema.required ?? []);
    const properties = Object.entries(schema.properties ?? {})
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([name, value]) => {
        const optional = required.has(name) ? "" : "?";
        return `readonly ${JSON.stringify(name)}${optional}: ${renderType(value)};`;
      });
    if (schema.additionalProperties) {
      properties.push(
        `[key: string]: ${schema.additionalProperties === true ? "unknown" : renderType(schema.additionalProperties)};`,
      );
    }
    return `{ ${properties.join(" ")} }`;
  }
  if (schema.type === "integer" || schema.type === "number") {
    return "number";
  }
  if (schema.type === "boolean") {
    return "boolean";
  }
  if (schema.type === "string") {
    return "string";
  }
  return "unknown";
}

const digest = createHash("sha256").update(canonicalOpenApi).digest("hex");
const paths = Object.keys(document.paths).sort();
const schemaTypes = Object.entries(schemas)
  .sort(([left], [right]) => left.localeCompare(right))
  .map(([name, schema]) => `export type ${name} = ${renderType(schema)};`)
  .join("\n\n");
const source = `// Generated from ewm.workbench.contracts. Do not edit by hand.
export const OPENAPI_SHA256 = ${JSON.stringify(digest)} as const;
export const API_VERSION = ${JSON.stringify(document.info.version)} as const;
export const API_PATHS = ${JSON.stringify(paths, null, 2)} as const;
export type ApiPath = (typeof API_PATHS)[number];

${schemaTypes}
`;

if (!existsSync(output) || readFileSync(output, "utf8") !== source) {
  writeFileSync(output, source, "utf8");
}
