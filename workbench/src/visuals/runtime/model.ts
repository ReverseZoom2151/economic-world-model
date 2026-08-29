import type { OntologyObjectContract } from "../../data/InvestigationDataSource";
import { ontologyObjectLabel } from "../shared/objectLabel";

export function eventSequence(event: OntologyObjectContract): number | null {
  const context = event.properties.context;
  if (typeof context !== "object" || context === null) {
    return null;
  }
  const sequence = (context as Readonly<Record<string, unknown>>).event_sequence;
  return typeof sequence === "number" && Number.isInteger(sequence) ? sequence : null;
}

export function eventLabel(event: OntologyObjectContract): string {
  return ontologyObjectLabel(event).replaceAll("_", " ");
}

export function orderedRuntimeEvents(
  events: ReadonlyArray<OntologyObjectContract>,
): ReadonlyArray<OntologyObjectContract> {
  return [...events].sort((left, right) => {
    const leftSequence = eventSequence(left) ?? Number.MAX_SAFE_INTEGER;
    const rightSequence = eventSequence(right) ?? Number.MAX_SAFE_INTEGER;
    return leftSequence - rightSequence || left.ref.id.localeCompare(right.ref.id);
  });
}
