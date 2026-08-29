import type { OntologyObjectContract } from "../../data/InvestigationDataSource";

const LABEL_FIELDS = [
  "natural_key",
  "label",
  "name",
  "role",
  "market",
  "learner",
  "mechanism",
  "intervention",
  "event_type",
  "action_type",
  "metric_name",
  "variable",
  "stage",
] as const;

export function ontologyKindLabel(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function numberProperty(
  object: OntologyObjectContract,
  ...keys: ReadonlyArray<string>
): number | null {
  for (const key of keys) {
    const value = object.properties[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
  }
  return null;
}

function sourceSequence(object: OntologyObjectContract): number | null {
  for (const source of object.sources) {
    const match = source.record_selector?.match(/(?:^|\b)sequence=(\d+)(?:\b|$)/);
    if (match?.[1] !== undefined) return Number(match[1]);
  }
  return null;
}

function eventKind(object: OntologyObjectContract): string | null {
  const event = object.properties.event;
  if (typeof event !== "object" || event === null) return null;
  const kind = (event as Readonly<Record<string, unknown>>).kind;
  return typeof kind === "string" && kind ? kind : null;
}

export function ontologyObjectSequence(object: OntologyObjectContract): number | null {
  const direct = numberProperty(object, "event_sequence", "sequence", "state_version");
  if (direct !== null) return direct;
  const context = object.properties.context;
  if (typeof context === "object" && context !== null) {
    const sequence = (context as Readonly<Record<string, unknown>>).event_sequence;
    if (typeof sequence === "number" && Number.isInteger(sequence)) return sequence;
  }
  const event = object.properties.event;
  if (typeof event === "object" && event !== null) {
    const sequence = (event as Readonly<Record<string, unknown>>).sequence;
    if (typeof sequence === "number" && Number.isInteger(sequence)) return sequence;
  }
  return sourceSequence(object);
}

function runtimeLabel(object: OntologyObjectContract): string | null {
  const sequence = ontologyObjectSequence(object);
  const suffix = sequence === null ? "" : ` · Event ${sequence}`;
  switch (object.ref.kind) {
    case "step": {
      const kind = eventKind(object);
      return `${kind === null ? "Runtime event" : ontologyKindLabel(kind)}${suffix}`;
    }
    case "mechanism_invocation": {
      const period = numberProperty(object, "state_version");
      return period === null ? `Market clearing${suffix}` : `Market clearing · Period ${period}`;
    }
    case "transaction":
      return `Aggregate cleared trade${suffix}`;
    case "outcome":
      return object.properties.outcome_kind === "order_rejections"
        ? `Order checks${suffix}`
        : `Market outcome${suffix}`;
    case "inner_equilibrium":
      return `Inner market equilibrium${suffix}`;
    case "equilibrium_witness":
      return `Price and volume witness${suffix}`;
    case "residual":
      return `Accounting residual${suffix}`;
    case "numerical_validation":
      return `Numerical validation${suffix}`;
    default:
      return null;
  }
}

function evidenceLabel(object: OntologyObjectContract): string | null {
  if (object.ref.kind === "claim") {
    const scope = object.properties.scope;
    return typeof scope === "string" && scope.toLowerCase().includes("fx")
      ? "Synthetic FX conformance observation"
      : "Bounded conformance observation";
  }
  if (object.ref.kind === "evidence_artifact") {
    const filename = object.properties.filename;
    return typeof filename === "string" && filename ? filename : "Verified run artifact";
  }
  return null;
}

export function ontologyObjectLabel(object: OntologyObjectContract): string {
  for (const field of LABEL_FIELDS) {
    const value = object.properties[field];
    if (typeof value !== "string" || !value.trim()) continue;
    const label = field === "natural_key" || field === "label" || field === "name"
      ? value.trim()
      : ontologyKindLabel(value.trim());
    const count = object.properties.count;
    return field === "role" && typeof count === "number" && count > 1
      ? `${label}s (${count})`
      : label;
  }
  const runtime = runtimeLabel(object);
  if (runtime !== null) return runtime;
  const evidence = evidenceLabel(object);
  if (evidence !== null) return evidence;
  return ontologyKindLabel(object.ref.kind);
}
