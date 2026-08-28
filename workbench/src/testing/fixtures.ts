import type { ComparisonRequest } from "../contracts/generated";
import type {
  ComparisonResultContract,
  InvestigationDataSource,
  MeasurementContract,
  ObjectQuery,
  OntologyObjectContract,
  Page,
  PathResultContract,
  RelationContract,
  RunSummary,
  SystemContract,
  WorkbenchStatus,
} from "../data/InvestigationDataSource";

const SOURCE = {
  record_type: "source_locator" as const,
  source_kind: "verified_run",
  source_id: "fixture-run",
  artifact_path: "events.jsonl",
  record_selector: "line:1",
  code_symbol: null,
  paper_anchor: null,
  payload_digest: "a".repeat(64),
};

export const FIXTURE_OBJECTS: ReadonlyArray<OntologyObjectContract> = [
  {
    record_type: "ontology_object",
    ref: {
      record_type: "ontology_ref",
      id: "ewm:fixture:agent:household",
      kind: "agent",
    },
    layer: "economic_declaration",
    properties: { natural_key: "Household 01" },
    sources: [SOURCE],
  },
  {
    record_type: "ontology_object",
    ref: {
      record_type: "ontology_ref",
      id: "ewm:fixture:claim:clearing",
      kind: "claim",
    },
    layer: "research_evidence",
    properties: {
      natural_key: "Market clearing claim",
      evidence_classification: "verified_run_evidence",
    },
    sources: [SOURCE],
  },
];

export const FIXTURE_RUNS: ReadonlyArray<RunSummary> = ["run-a", "run-b"].map(
  (runId, index) => ({
    run_id: runId,
    source_run_hash: String(index + 1).repeat(20),
    profile_identity: "ewm.scalar.v1",
    integrity_level: "checksummed",
    projection_digest: String(index + 2).repeat(64),
    ontology_schema: "ewm.ontology.v1",
  }),
);

function page<T>(items: ReadonlyArray<T>): Page<T> {
  return { items, next_cursor: null };
}

class FixtureDataSource implements InvestigationDataSource {
  readonly #status: WorkbenchStatus;
  readonly #runs: ReadonlyArray<RunSummary>;

  constructor(status: WorkbenchStatus, runs: ReadonlyArray<RunSummary>) {
    this.#status = status;
    this.#runs = runs;
  }

  async system(): Promise<SystemContract> {
    return {
      api_major: 1,
      api_minor: 0,
      mode: "fixture",
      run_count: this.#runs.length,
      status: this.#status,
    };
  }

  async runs(): Promise<ReadonlyArray<RunSummary>> {
    return this.#runs;
  }

  async run(id: string): Promise<RunSummary> {
    const run = this.#runs.find((candidate) => candidate.run_id === id);
    if (run === undefined) {
      throw new Error(`unknown fixture run ${id}`);
    }
    return run;
  }

  async object(_runId: string, id: string): Promise<OntologyObjectContract> {
    const object = FIXTURE_OBJECTS.find((candidate) => candidate.ref.id === id);
    if (object === undefined) {
      throw new Error(`unknown fixture object ${id}`);
    }
    return object;
  }

  async objects(query: ObjectQuery): Promise<Page<OntologyObjectContract>> {
    return page(
      FIXTURE_OBJECTS.filter(
        (object) =>
          (!query.kinds?.length || query.kinds.includes(object.ref.kind)) &&
          (!query.layers?.length || query.layers.includes(object.layer)),
      ),
    );
  }

  async relations(): Promise<Page<RelationContract>> {
    return page([]);
  }

  async paths(): Promise<PathResultContract> {
    return { paths: [], truncated: false, visited_records: 0 };
  }

  async events(): Promise<Page<OntologyObjectContract>> {
    return page([]);
  }

  async states(): Promise<Page<OntologyObjectContract>> {
    return page([]);
  }

  async measurements(): Promise<Page<MeasurementContract>> {
    return page([]);
  }

  async claims(): Promise<Page<OntologyObjectContract>> {
    return page(FIXTURE_OBJECTS.filter((object) => object.ref.kind === "claim"));
  }

  async evidence(): Promise<Page<OntologyObjectContract>> {
    return page([]);
  }

  async ddge(): Promise<Page<OntologyObjectContract>> {
    return page([]);
  }

  async compare(request: ComparisonRequest): Promise<ComparisonResultContract> {
    return {
      comparison_id: `${request.left_run_id}:${request.right_run_id}`,
      result: {},
    };
  }
}

export function createFixtureDataSource(
  options: {
    readonly status?: WorkbenchStatus;
    readonly runs?: ReadonlyArray<RunSummary>;
  } = {},
): InvestigationDataSource {
  return new FixtureDataSource(options.status ?? "ready", options.runs ?? FIXTURE_RUNS);
}

interface DeferredResult {
  readonly status: WorkbenchStatus;
  readonly runs: ReadonlyArray<RunSummary>;
}

export function deferredDataSource(): {
  readonly source: InvestigationDataSource;
  readonly resolve: (result: DeferredResult) => void;
} {
  let resolvePromise: (result: DeferredResult) => void = () => undefined;
  const result = new Promise<DeferredResult>((resolve) => {
    resolvePromise = resolve;
  });
  const delegate = createFixtureDataSource();
  return {
    source: {
      async system() {
        const value = await result;
        return {
          api_major: 1,
          api_minor: 0,
          mode: "fixture",
          run_count: value.runs.length,
          status: value.status,
        };
      },
      async runs() {
        return (await result).runs;
      },
      run: (id) => delegate.run(id),
      object: (runId, id) => delegate.object(runId, id),
      objects: (query) => delegate.objects(query),
      relations: (query) => delegate.relations(query),
      paths: (query) => delegate.paths(query),
      events: (query) => delegate.events(query),
      states: (query) => delegate.states(query),
      measurements: (query) => delegate.measurements(query),
      claims: (query) => delegate.claims(query),
      evidence: (query) => delegate.evidence(query),
      ddge: (query) => delegate.ddge(query),
      compare: (request) => delegate.compare(request),
    },
    resolve: resolvePromise,
  };
}
