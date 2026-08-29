import type {
  CoverageContract,
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { TechnicalDetails } from "../provenance/TechnicalDetails";
import { ontologyObjectLabel } from "../shared/objectLabel";

interface LearningClosureProps {
  readonly objects: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
  readonly coverage: ReadonlyArray<CoverageContract>;
}

const STAGES = [
  { kind: "parameter_version", label: "Deployment parameter" },
  { kind: "action_occurrence", label: "Behavior" },
  { kind: "generated_datum", label: "Generated data" },
  { kind: "dataset", label: "Dataset" },
  { kind: "training_run", label: "Training" },
  { kind: "model_version", label: "Learned model" },
] as const;

function objectsOfKind(
  objects: ReadonlyArray<OntologyObjectContract>,
  kind: string,
): ReadonlyArray<OntologyObjectContract> {
  return objects.filter((object) => object.ref.kind === kind);
}

function relationExists(
  relations: ReadonlyArray<RelationContract>,
  type: string,
  sourceKind: string,
  targetKind: string,
  records: ReadonlyMap<string, OntologyObjectContract>,
): boolean {
  return relations.some(
    (relation) =>
      relation.relation_type === type &&
      records.get(relation.source.id)?.ref.kind === sourceKind &&
      records.get(relation.target.id)?.ref.kind === targetKind,
  );
}

function propertyText(object: OntologyObjectContract | undefined, key: string): string {
  const value = object?.properties[key];
  return typeof value === "string" ? value : "unavailable";
}

function readableProperty(object: OntologyObjectContract | undefined, key: string): string {
  const value = propertyText(object, key);
  return value === "unavailable" ? value : value.replaceAll("_", " ");
}

export function LearningClosure({ objects, relations, coverage }: LearningClosureProps) {
  const records = new Map(objects.map((object) => [object.ref.id, object]));
  const dataset = objectsOfKind(objects, "dataset")[0];
  const training = objectsOfKind(objects, "training_run")[0];
  const parameter = objectsOfKind(objects, "parameter_version")[0];
  const included =
    dataset === undefined
      ? []
      : relations.filter(
          (relation) =>
            relation.relation_type === "INCLUDED_IN" &&
            relation.target.id === dataset.ref.id &&
            records.get(relation.source.id)?.ref.kind === "generated_datum",
        );
  const linked =
    STAGES.every((stage) => objectsOfKind(objects, stage.kind).length > 0) &&
    relationExists(relations, "GENERATES", "action_occurrence", "generated_datum", records) &&
    included.length > 0 &&
    relationExists(relations, "TRAINS", "dataset", "training_run", records) &&
    relationExists(relations, "PRODUCES", "training_run", "model_version", records) &&
    relationExists(relations, "DEPLOYS", "model_version", "parameter_version", records);
  const gaps = coverage.filter((entry) => entry.status !== "projected");

  return (
    <div className="learning-closure">
      <p className="stage-scroll-hint">Six-stage closure · scroll horizontally to inspect</p>
      <ol aria-label="Learning closure stages">
        {STAGES.map((stage, index) => {
          const stageObjects = objectsOfKind(objects, stage.kind);
          return (
            <li key={stage.kind} data-stage-status={stageObjects.length ? "available" : "unavailable"}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{stage.label}</strong>
              <small>
                {stageObjects.length
                  ? `${stageObjects.length} ${stageObjects.length === 1 ? "record" : "records"}`
                  : `${stage.label} stage unavailable`}
              </small>
            </li>
          );
        })}
      </ol>
      <section className="closure-detail" aria-label="Dataset and training identity">
        <dl>
          <div>
            <dt>Dataset membership</dt>
            <dd>{included.length} included records</dd>
          </div>
          <div>
            <dt>Learner</dt>
            <dd>{readableProperty(training, "learner")}</dd>
          </div>
          <div>
            <dt>Training status</dt>
            <dd>{readableProperty(training, "status")}</dd>
          </div>
          <div>
            <dt>Deployed parameter</dt>
            <dd>{parameter === undefined ? "unavailable" : ontologyObjectLabel(parameter)}</dd>
          </div>
        </dl>
        <TechnicalDetails
          details={[
            { label: "Dataset identity", value: dataset?.ref.id },
            { label: "Training identity", value: training?.ref.id },
            { label: "Deployment identity", value: parameter?.ref.id },
          ]}
        />
      </section>
      <aside className="closure-gaps" aria-label="Learning closure gaps">
        <strong>{linked ? "Closure linked" : "Closure incomplete"}</strong>
        {gaps.length > 0 ? (
          <ul>
            {gaps.map((gap) => (
              <li key={`${gap.field}:${gap.status}`}>
                <span>{gap.field.split(".").at(-1)?.replaceAll("_", " ") ?? gap.field}</span>
                <p>{gap.reason ?? gap.status}</p>
              </li>
            ))}
          </ul>
        ) : null}
      </aside>
    </div>
  );
}
