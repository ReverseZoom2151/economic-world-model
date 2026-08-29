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

function words(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function ontologyObjectLabel(object: OntologyObjectContract): string {
  for (const field of LABEL_FIELDS) {
    const value = object.properties[field];
    if (typeof value !== "string" || !value.trim()) continue;
    const label = field === "natural_key" || field === "label" || field === "name"
      ? value.trim()
      : words(value.trim());
    const count = object.properties.count;
    return field === "role" && typeof count === "number" && count > 1
      ? `${label}s (${count})`
      : label;
  }
  const identityTail = object.ref.id.split(":").filter(Boolean).at(-1) ?? "record";
  return `${words(object.ref.kind)} · ${words(identityTail)}`;
}
