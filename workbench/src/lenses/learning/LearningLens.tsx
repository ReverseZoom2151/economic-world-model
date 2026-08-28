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
}

export function LearningLens({ objects, relations, coverage }: LearningLensProps) {
  return (
    <article className="lens-surface learning-lens">
      <header className="lens-heading">
        <div>
          <p>Learning / closure</p>
          <h2>Behavior-to-learning closure</h2>
        </div>
        <strong>Exact ontology stages</strong>
      </header>
      <LearningClosure objects={objects} relations={relations} coverage={coverage} />
    </article>
  );
}
