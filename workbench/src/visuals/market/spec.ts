import type { TopLevelSpec } from "vega-lite";

import type { MeasurementContract } from "../../data/InvestigationDataSource";

function requiredText(value: unknown, label: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`market measurement ${label} is required`);
  }
  return value;
}

export function sampleSize(sample: Readonly<Record<string, unknown>>): number {
  const size = sample.sample_size;
  if (typeof size !== "number" || !Number.isInteger(size) || size <= 0) {
    throw new Error("market measurement sample size is required");
  }
  return size;
}

export function uncertaintyLabel(uncertainty: Readonly<Record<string, unknown>>): string {
  const method = requiredText(uncertainty.method, "uncertainty method");
  const value = uncertainty.value;
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error("market measurement uncertainty value is required");
  }
  return `${method} · ${value}`;
}

export function sourceLabel(measurement: MeasurementContract): string {
  const source = measurement.sources[0];
  if (source === undefined) {
    throw new Error("market measurement source is required");
  }
  return `${source.source_kind.replaceAll("_", " ")} · ${source.source_id}`;
}

function validateMeasurement(measurement: MeasurementContract): void {
  requiredText(measurement.unit, "unit");
  requiredText(measurement.name, "name");
  sampleSize(measurement.sample);
  uncertaintyLabel(measurement.uncertainty);
  sourceLabel(measurement);
  if (typeof measurement.value !== "number" || !Number.isFinite(measurement.value)) {
    throw new Error("market measurement value must be finite and numeric");
  }
}

export function marketMeasurementIssue(measurement: MeasurementContract): string | null {
  try {
    validateMeasurement(measurement);
    return null;
  } catch (error) {
    return error instanceof Error ? error.message : "market measurement metadata is invalid";
  }
}

export function buildMarketSpec(
  measurements: ReadonlyArray<MeasurementContract>,
): TopLevelSpec {
  if (measurements.length === 0) {
    throw new Error("at least one market measurement is required");
  }
  const groups = new Map<string, MeasurementContract[]>();
  for (const measurement of measurements) {
    validateMeasurement(measurement);
    const unit = measurement.unit;
    groups.set(unit, [...(groups.get(unit) ?? []), measurement]);
  }
  return {
    background: "transparent",
    spacing: 20,
    vconcat: [...groups]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([unit, group]) => ({
        width: "container",
        height: 130,
        data: {
          values: group.map((measurement) => ({
            name: measurement.name,
            status: measurement.status,
            value: measurement.value,
          })),
        },
        mark: { type: "point", filled: true, size: 85 },
        encoding: {
          x: {
            field: "name",
            type: "nominal",
            axis: { labelAngle: 0, title: null },
          },
          y: {
            field: "value",
            type: "quantitative",
            axis: { title: `Value (${unit})`, zero: false },
          },
          color: {
            field: "status",
            type: "nominal",
            scale: { range: ["#0072b2", "#e69f00", "#5f6360"] },
          },
          shape: { field: "status", type: "nominal" },
          tooltip: [
            { field: "name", type: "nominal" },
            { field: "value", type: "quantitative", title: `Value (${unit})` },
            { field: "status", type: "nominal" },
          ],
        },
      })),
  };
}
