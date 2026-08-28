import type { OntologyObjectContract } from "../../data/InvestigationDataSource";
import { formattedNumber, propertyNumber, propertyText } from "./model";

interface CandidateBasinsProps {
  readonly candidates: ReadonlyArray<OntologyObjectContract>;
  readonly correspondence: OntologyObjectContract | null;
}

export function CandidateBasins({ candidates, correspondence }: CandidateBasinsProps) {
  const selector = correspondence === null ? null : propertyText(correspondence, "selector");
  return (
    <section className="candidate-basins" aria-labelledby="candidate-basins-title">
      <header>
        <h3 id="candidate-basins-title">Candidates and basins</h3>
        <div>
          <span>Selector</span>
          <strong>{selector ?? "No preferred candidate selected"}</strong>
        </div>
      </header>
      {candidates.length === 0 ? (
        <p>No DDGE candidates were projected.</p>
      ) : (
        <ol>
          {candidates.map((candidate, index) => {
            const theta = propertyNumber(candidate, "theta");
            const stable = candidate.properties.stable;
            return (
              <li key={candidate.ref.id}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong>{candidate.ref.id}</strong>
                  <small>{propertyText(candidate, "status")?.replaceAll("_", " ") ?? "observed"}</small>
                </div>
                <dl>
                  <div>
                    <dt>θ</dt>
                    <dd>{theta === null ? "unavailable" : formattedNumber(theta)}</dd>
                  </div>
                  <div>
                    <dt>Basin</dt>
                    <dd>{propertyText(candidate, "basin") ?? "unavailable"}</dd>
                  </div>
                  <div>
                    <dt>Initialization</dt>
                    <dd>
                      {propertyNumber(candidate, "initialization") === null
                        ? "unavailable"
                        : formattedNumber(propertyNumber(candidate, "initialization")!)}
                    </dd>
                  </div>
                  <div>
                    <dt>Stability</dt>
                    <dd>{stable === true ? "Stable" : stable === false ? "Unstable" : "Unavailable"}</dd>
                  </div>
                </dl>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
