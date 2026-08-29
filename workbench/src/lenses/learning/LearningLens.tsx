import type {
  CoverageContract,
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { LearningClosure } from "../../visuals/learning/LearningClosure";

interface LearningLensProps {
  readonly objects: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
  readonly coverage: ReadonlyArray<CoverageContract>;
  readonly bounded?: boolean;
}

export function LearningLens({ objects, relations, coverage, bounded = false }: LearningLensProps) {
  return (
    <article className="lens-surface learning-lens">
      <header className="lens-heading">
        <div>
          <p>Learning / closure</p>
          <h2>Behavior-to-learning closure</h2>
        </div>
        <strong>Exact ontology stages</strong>
      </header>
      {bounded ? (
        <p className="bounded-notice">
          This view shows the first bounded page of records and explicit coverage gaps.
        </p>
      ) : null}
      <LearningClosure objects={objects} relations={relations} coverage={coverage} />
    </article>
  );
}
