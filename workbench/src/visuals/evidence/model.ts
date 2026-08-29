import type { OntologyObjectContract } from "../../data/InvestigationDataSource";
import { ontologyObjectLabel } from "../shared/objectLabel";

export function objectLabel(object: OntologyObjectContract): string {
  return ontologyObjectLabel(object);
}

export function classification(object: OntologyObjectContract): string {
  const value = object.properties.evidence_classification;
  return typeof value === "string" && value.trim() ? value : "unclassified";
}

export function limitations(object: OntologyObjectContract): ReadonlyArray<string> {
  const value = object.properties.limitations ?? object.properties.limitation;
  if (typeof value === "string" && value.trim()) {
    return [value];
  }
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
}

export function statusShape(value: string): string {
  const shapes: Readonly<Record<string, string>> = {
    verified_run_evidence: "◇",
    empirical_observation: "●",
    synthetic_conformance: "△",
    theorem_backed: "□",
    not_measured: "○",
  };
  return shapes[value] ?? "?";
}
