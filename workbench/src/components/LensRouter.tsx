import { useEffect, useState } from "react";

import type {
  CoverageContract,
  InvestigationDataSource,
  MeasurementContract,
  OntologyObjectContract,
  RelationContract,
} from "../data/InvestigationDataSource";
import { CompareLens } from "../lenses/compare/CompareLens";
import { DdgeLens } from "../lenses/ddge/DdgeLens";
import { EvidenceLens } from "../lenses/evidence/EvidenceLens";
import { GlobeLens } from "../lenses/globe/GlobeLens";
import { LearningLens } from "../lenses/learning/LearningLens";
import { LineageLens } from "../lenses/lineage/LineageLens";
import { MarketLens } from "../lenses/market/MarketLens";
import { RuntimeLens } from "../lenses/runtime/RuntimeLens";
import { SceneLens } from "../lenses/scene/SceneLens";
import { WorldLens } from "../lenses/world/WorldLens";
import { CANONICAL_SCENE_CAMERA } from "../scene/camera";
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
  scene: "Deterministic semantic lanes, ontology layers, and declared temporal depth.",
  globe: "Explicit sourced coordinates, validity, uncertainty, and bounded geographic flows.",
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
  readonly coverage: ReadonlyArray<CoverageContract>;
  readonly failed: boolean;
}

const EMPTY_DATA: PrimaryLensData = {
  key: "",
  objects: [],
  relations: [],
  events: [],
  measurements: [],
  coverage: [],
  failed: false,
};

type ImplementedLens = "world" | "runtime" | "market" | "learning" | "ddge";

function isImplementedLens(lens: InvestigationLens): lens is ImplementedLens {
  return ["world", "runtime", "market", "learning", "ddge"].includes(lens);
}

async function loadLens(
  dataSource: InvestigationDataSource,
  runId: string,
  lens: ImplementedLens,
): Promise<Omit<PrimaryLensData, "key" | "failed">> {
  if (lens === "world") {
    const [objects, relations] = await Promise.all([
      dataSource.objects({ runId, layers: ["economic_declaration"], limit: 200 }),
      dataSource.relations({ runId, limit: 200 }),
    ]);
    return {
      objects: objects.items,
      relations: relations.items,
      events: [],
      measurements: [],
      coverage: [],
    };
  }
  if (lens === "runtime") {
    const [events, relations] = await Promise.all([
      dataSource.events({ runId, limit: 200 }),
      dataSource.relations({ runId, limit: 200 }),
    ]);
    return {
      objects: [],
      relations: relations.items,
      events: events.items,
      measurements: [],
      coverage: [],
    };
  }
  if (lens === "market") {
    const [measurements, events] = await Promise.all([
      dataSource.measurements({ runId, limit: 200 }),
      dataSource.events({ runId, limit: 200 }),
    ]);
    return {
      objects: [],
      relations: [],
      events: events.items.filter(
        (event) =>
          event.ref.kind === "market_rejection" ||
          (event.ref.kind === "outcome" &&
            event.properties.outcome_kind === "order_rejections"),
      ),
      measurements: measurements.items,
      coverage: [],
    };
  }
  const kinds =
    lens === "learning"
      ? [
          "parameter_version",
          "action_occurrence",
          "generated_datum",
          "dataset",
          "training_run",
          "model_version",
        ]
      : [
          "inner_equilibrium",
          "ddge_candidate",
          "residual",
          "numerical_validation",
          "stability_diagnostic",
          "theorem_certificate",
        ];
  const [objects, relations, run] = await Promise.all([
    dataSource.objects({ runId, kinds, limit: 200 }),
    dataSource.relations({ runId, limit: 200 }),
    dataSource.run(runId),
  ]);
  return {
    objects: objects.items,
    relations: relations.items,
    events: [],
    measurements: [],
    coverage: run.coverage ?? [],
  };
}

export function LensRouter({ dataSource }: LensRouterProps) {
  const { state, dispatch } = useInvestigation();
  const requestKey = `${state.runId ?? ""}|${state.lens}`;
  const [result, setResult] = useState<PrimaryLensData>(EMPTY_DATA);

  useEffect(() => {
    let active = true;
    if (state.runId === null || !isImplementedLens(state.lens)) {
      return;
    }
    void loadLens(dataSource, state.runId, state.lens)
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

  if (state.runId !== null && state.lens === "compare") {
    return (
      <section className="lens-slot" aria-label="Active analytical lens">
        <CompareLens dataSource={dataSource} activeRunId={state.runId} />
      </section>
    );
  }
  if (state.runId !== null && state.lens === "evidence") {
    return (
      <section className="lens-slot" aria-label="Active analytical lens">
        <EvidenceLens dataSource={dataSource} runId={state.runId} />
      </section>
    );
  }
  if (state.runId !== null && state.lens === "lineage") {
    return (
      <section className="lens-slot" aria-label="Active analytical lens">
        <LineageLens
          dataSource={dataSource}
          runId={state.runId}
          selectedId={state.objectId}
        />
      </section>
    );
  }
  if (state.runId !== null && state.lens === "scene") {
    return (
      <section className="lens-slot" aria-label="Active analytical lens">
        <SceneLens
          dataSource={dataSource}
          runId={state.runId}
          selectedId={state.objectId}
          camera={state.camera ?? CANONICAL_SCENE_CAMERA}
          onCameraChange={(camera) => dispatch({ type: "set-camera", camera })}
          onSelect={(objectId) => dispatch({ type: "select-object", objectId })}
        />
      </section>
    );
  }
  if (state.runId !== null && state.lens === "globe") {
    const comparisonRunId =
      state.comparison === null
        ? null
        : state.comparison.leftRunId === state.runId
          ? state.comparison.rightRunId
          : state.comparison.leftRunId;
    return (
      <section className="lens-slot" aria-label="Active analytical lens">
        <GlobeLens
          dataSource={dataSource}
          runId={state.runId}
          comparisonRunId={comparisonRunId}
          selectedId={state.objectId}
          time={state.timeWindow?.end ?? null}
          onSelect={(objectId) => dispatch({ type: "select-object", objectId })}
        />
      </section>
    );
  }

  if (state.runId !== null && isImplementedLens(state.lens)) {
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
    if (state.lens === "market") {
      return (
        <section className="lens-slot" aria-label="Active analytical lens">
          <MarketLens measurements={result.measurements} rejections={result.events} />
        </section>
      );
    }
    if (state.lens === "learning") {
      return (
        <section className="lens-slot" aria-label="Active analytical lens">
          <LearningLens
            objects={result.objects}
            relations={result.relations}
            coverage={result.coverage}
          />
        </section>
      );
    }
    return (
      <section className="lens-slot" aria-label="Active analytical lens">
        <DdgeLens objects={result.objects} relations={result.relations} />
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
