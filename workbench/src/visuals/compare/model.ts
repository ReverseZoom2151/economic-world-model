import type { ComparisonResultContract } from "../../data/InvestigationDataSource";

export type UnknownRecord = Readonly<Record<string, unknown>>;

export function record(value: unknown): UnknownRecord | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as UnknownRecord)
    : null;
}

export function records(value: unknown): ReadonlyArray<UnknownRecord> {
  return Array.isArray(value)
    ? value.map(record).filter((item): item is UnknownRecord => item !== null)
    : [];
}

export function text(value: unknown, fallback = "not recorded"): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function printable(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => printable(item)).join(", ");
  }
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }
  return value === null || value === undefined ? "not recorded" : JSON.stringify(value);
}

export function comparisonSections(result: ComparisonResultContract): {
  readonly preflight: UnknownRecord | null;
  readonly aligned: ReadonlyArray<UnknownRecord>;
  readonly unaligned: ReadonlyArray<UnknownRecord>;
} {
  return {
    preflight: record(result.result.preflight),
    aligned: records(result.result.aligned),
    unaligned: records(result.result.unaligned),
  };
}
