import { useEffect, useState } from "react";

import type {
  InvestigationDataSource,
  MeasurementContract,
  OntologyObjectContract,
  RelationContract,
} from "../data/InvestigationDataSource";
import { MarketLens } from "../lenses/market/MarketLens";
import { RuntimeLens } from "../lenses/runtime/RuntimeLens";
import { WorldLens } from "../lenses/world/WorldLens";
import { useInvestigation, type InvestigationLens } from "../state/investigation";

const DESCRIPTIONS: Readonly<Record<InvestigationLens, string>> = {
  world: "Declared agents, institutions, markets, data, and model boundaries.",
  runtime: "Observed states, actions, transitions, settlements, and event order.",
  market: "Orders, clearing, prices, volumes, constraints, and rejections.",
  learning: "Generated datasets, training runs, learned parameters, and deployments.",
  ddge: "Candidate fixed points, residuals, stability, basins, and certificates.",
  compare: "Compatible measurements and every rejected alignment decision.",
  evidence: "Claims, evidence classifications, protocols, sources, and limitations.",
  lineage: "Derivation paths from runtime records back to artifacts and code.",
};

function title(lens: InvestigationLens): string {
  return lens === "ddge" ? "DDGE" : `${lens[0]?.toUpperCase()}${lens.slice(1)}`;
}

interface LensRouterProps {
  readonly dataSource: InvestigationDataSource;
}

interface PrimaryLensData {
  readonly key: string;
  readonly objects: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
  readonly events: ReadonlyArray<OntologyObjectContract>;
  readonly measurements: ReadonlyArray<MeasurementContract>;
  readonly failed: boolean;
}

const EMPTY_DATA: PrimaryLensData = {
  key: "",
  objects: [],
  relations: [],
  events: [],
  measurements: [],
  failed: false,
};

function isPrimaryLens(lens: InvestigationLens): lens is "world" | "runtime" | "market" {
  return lens === "world" || lens === "runtime" || lens === "market";
}

export function LensRouter({ dataSource }: LensRouterProps) {
  const { state, dispatch } = useInvestigation();
  const requestKey = `${state.runId ?? ""}|${state.lens}`;
  const [result, setResult] = useState<PrimaryLensData>(EMPTY_DATA);

  useEffect(() => {
    let active = true;
    if (state.runId === null || !isPrimaryLens(state.lens)) {
      return;
    }
    const runId = state.runId;
    const relations = dataSource.relations({ runId, limit: 200 });
    const request =
      state.lens === "world"
        ? Promise.all([
            dataSource.objects({
              runId,
              layers: ["economic_declaration"],
              limit: 200,
            }),
            relations,
          ]).then(([objects, relationPage]) => ({
            objects: objects.items,
            relations: relationPage.items,
            events: [],
            measurements: [],
          }))
        : state.lens === "runtime"
          ? Promise.all([dataSource.events({ runId, limit: 200 }), relations]).then(
              ([events, relationPage]) => ({
                objects: [],
                relations: relationPage.items,
                events: events.items,
                measurements: [],
              }),
            )
          : Promise.all([
              dataSource.measurements({ runId, limit: 200 }),
              dataSource.events({ runId, limit: 200 }),
            ]).then(([measurements, events]) => ({
              objects: [],
              relations: [],
              events: events.items.filter(
                (event) =>
                  event.ref.kind === "market_rejection" ||
                  (event.ref.kind === "outcome" &&
                    event.properties.outcome_kind === "order_rejections"),
              ),
              measurements: measurements.items,
            }));
    void request
      .then((data) => {
        if (active) {
          setResult({ key: requestKey, ...data, failed: false });
        }
      })
      .catch(() => {
        if (active) {
          setResult({ ...EMPTY_DATA, key: requestKey, failed: true });
        }
      });
    return () => {
      active = false;
    };
  }, [dataSource, requestKey, state.lens, state.runId]);

  if (state.runId !== null && isPrimaryLens(state.lens)) {
    if (result.key !== requestKey) {
      return (
        <section className="lens-slot" aria-label="Active analytical lens">
          <p className="lens-loading">Loading {state.lens} projection…</p>
        </section>
      );
    }
    if (result.failed) {
      return (
        <section className="lens-slot" aria-label="Active analytical lens">
          <p className="sparse-fallback" role="alert">
            The {state.lens} lens could not read its bounded projection.
          </p>
        </section>
      );
    }
    if (state.lens === "world") {
      return (
        <section className="lens-slot" aria-label="Active analytical lens">
          <WorldLens
            objects={result.objects}
            relations={result.relations}
            selectedId={state.objectId}
            onSelect={(objectId) => dispatch({ type: "select-object", objectId })}
          />
        </section>
      );
    }
    if (state.lens === "runtime") {
      return (
        <section className="lens-slot" aria-label="Active analytical lens">
          <RuntimeLens
            events={result.events}
            relations={result.relations}
            timeWindow={state.timeWindow}
            selectedId={state.objectId}
            onSelect={(objectId) => dispatch({ type: "select-object", objectId })}
          />
        </section>
      );
    }
    return (
      <section className="lens-slot" aria-label="Active analytical lens">
        <MarketLens measurements={result.measurements} rejections={result.events} />
      </section>
    );
  }

  return (
    <section className="active-lens" aria-label="Active analytical lens">
      <div className="active-lens__coordinate">02 / {state.lens.toUpperCase()}</div>
      <div className="active-lens__field">
        <p>Analytical surface</p>
        <h2>{title(state.lens)} lens</h2>
        <p>{DESCRIPTIONS[state.lens]}</p>
        <div className="active-lens__placeholder">
          <span aria-hidden="true">↳</span>
          <p>The shared selection boundary is ready for this lens.</p>
          <small>Scientific encodings arrive as isolated, tested visual modules.</small>
        </div>
      </div>
    </section>
  );
}
