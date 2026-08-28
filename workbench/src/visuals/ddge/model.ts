import type {
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";

export function objectsByKind(
  objects: ReadonlyArray<OntologyObjectContract>,
  kind: string,
): ReadonlyArray<OntologyObjectContract> {
  return objects
    .filter((object) => object.ref.kind === kind)
    .sort((left, right) => left.ref.id.localeCompare(right.ref.id));
}

export function linkedTargets(
  sourceId: string,
  relationType: string,
  relations: ReadonlyArray<RelationContract>,
  objects: ReadonlyMap<string, OntologyObjectContract>,
): ReadonlyArray<OntologyObjectContract> {
  return relations
    .filter(
      (relation) => relation.relation_type === relationType && relation.source.id === sourceId,
    )
    .map((relation) => objects.get(relation.target.id))
    .filter((object): object is OntologyObjectContract => object !== undefined)
    .sort((left, right) => left.ref.id.localeCompare(right.ref.id));
}

export function propertyNumber(
  object: OntologyObjectContract,
  key: string,
): number | null {
  const value = object.properties[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function propertyText(
  object: OntologyObjectContract,
  key: string,
): string | null {
  const value = object.properties[key];
  return typeof value === "string" && value.trim() ? value : null;
}

export function formattedNumber(value: number): string {
  const rendered = String(value);
  return rendered.startsWith("-") ? `−${rendered.slice(1)}` : rendered;
}
