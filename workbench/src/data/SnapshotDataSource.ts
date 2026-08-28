import type { ComparisonRequest } from "../contracts/generated";
import type {
  ClassificationQuery,
  ComparisonResultContract,
  CoverageContract,
  EventQuery,
  InvestigationDataSource,
  MeasurementContract,
  MeasurementQuery,
  ObjectQuery,
  OntologyObjectContract,
  Page,
  PathContract,
  PathQuery,
  PathResultContract,
  RelationContract,
  RelationQuery,
  RunSummary,
  SystemContract,
} from "./InvestigationDataSource";

export interface SnapshotSelectionContract {
  readonly object_ids: ReadonlyArray<string>;
  readonly relation_ids: ReadonlyArray<string>;
  readonly event_ids: ReadonlyArray<string>;
  readonly lens: string;
  readonly filters: {
    readonly kinds: ReadonlyArray<string>;
    readonly layers: ReadonlyArray<string>;
    readonly query: string;
  };
  readonly time_window: { readonly start: number; readonly end: number } | null;
  readonly camera: {
    readonly projection: "perspective" | "orthographic";
    readonly position: readonly [number, number, number];
    readonly target: readonly [number, number, number];
  } | null;
  readonly layout: Readonly<Record<string, unknown>>;
}

export interface InvestigationSnapshot {
  readonly schema: "ewm.investigation.v1";
  readonly source_run_hash: string;
  readonly source_identity_sha256: string;
  readonly source_bundle_sha256: string;
  readonly profile_identity: string;
  readonly profile_digest: string;
  readonly integrity_level: string;
  readonly projection_digest: string;
  readonly subset_digest: string;
  readonly selection: SnapshotSelectionContract;
  readonly runs: ReadonlyArray<RunSummary>;
  readonly objects: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
  readonly measurements: ReadonlyArray<MeasurementContract>;
  readonly coverage: ReadonlyArray<CoverageContract>;
  readonly comparisons: ReadonlyArray<ComparisonResultContract>;
  readonly globe_geometry: Readonly<Record<string, unknown>> | null;
}

export class SnapshotDataSourceError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "SnapshotDataSourceError";
    this.code = code;
  }
}

function assertSnapshot(value: InvestigationSnapshot): void {
  if (
    value.schema !== "ewm.investigation.v1" ||
    !/^[a-f0-9]{64}$/.test(value.projection_digest) ||
    !/^[a-f0-9]{64}$/.test(value.subset_digest) ||
    value.runs.length !== 1 ||
    !Array.isArray(value.objects) ||
    !Array.isArray(value.relations) ||
    !Array.isArray(value.measurements)
  ) {
    throw new SnapshotDataSourceError(
      "invalid_snapshot",
      "embedded data does not match ewm.investigation.v1",
    );
  }
}

function cursorOffset(cursor: string | undefined): number {
  if (cursor === undefined) {
    return 0;
  }
  try {
    const decoded = atob(cursor);
    if (!/^ewm-snapshot:\d+$/.test(decoded)) {
      throw new Error("invalid cursor");
    }
    return Number(decoded.slice("ewm-snapshot:".length));
  } catch {
    throw new SnapshotDataSourceError("invalid_cursor", "snapshot cursor is invalid");
  }
}

function page<T>(
  values: ReadonlyArray<T>,
  limit: number | undefined,
  cursor: string | undefined,
): Page<T> {
  const selectedLimit = limit ?? 200;
  if (!Number.isInteger(selectedLimit) || selectedLimit < 1 || selectedLimit > 200) {
    throw new SnapshotDataSourceError(
      "query_cost",
      "snapshot query limit must be between 1 and 200",
    );
  }
  const offset = cursorOffset(cursor);
  if (offset > values.length) {
    throw new SnapshotDataSourceError("invalid_cursor", "snapshot cursor exceeds data");
  }
  const items = values.slice(offset, offset + selectedLimit);
  const nextOffset = offset + items.length;
  return {
    items,
    next_cursor:
      nextOffset < values.length ? btoa(`ewm-snapshot:${nextOffset}`) : null,
  };
}

function classification(object: OntologyObjectContract): string | undefined {
  const value = object.properties.evidence_classification;
  return typeof value === "string" ? value : undefined;
}

function orderedEvents(
  objects: ReadonlyArray<OntologyObjectContract>,
): ReadonlyArray<OntologyObjectContract> {
  return objects
    .filter((object) => object.layer === "runtime_occurrence")
    .toSorted((left, right) => {
      const leftSequence = Number(left.properties.event_sequence ?? Number.MAX_SAFE_INTEGER);
      const rightSequence = Number(right.properties.event_sequence ?? Number.MAX_SAFE_INTEGER);
      return leftSequence - rightSequence || left.ref.id.localeCompare(right.ref.id);
    });
}

export class SnapshotDataSource implements InvestigationDataSource {
  readonly #snapshot: InvestigationSnapshot;
  readonly #runId: string;

  constructor(snapshot: InvestigationSnapshot) {
    assertSnapshot(snapshot);
    this.#snapshot = snapshot;
    this.#runId = snapshot.runs[0]!.run_id;
  }

  #assertRun(runId: string): void {
    if (runId !== this.#runId) {
      throw new SnapshotDataSourceError(
        "not_available",
        `run ${runId} is not available in this snapshot`,
      );
    }
  }

  async system(): Promise<SystemContract> {
    return {
      api_major: 1,
      api_minor: 0,
      mode: "offline-snapshot",
      run_count: 1,
      status: "ready",
    };
  }

  async runs(): Promise<ReadonlyArray<RunSummary>> {
    return this.#snapshot.runs;
  }

  async run(id: string): Promise<RunSummary> {
    this.#assertRun(id);
    return this.#snapshot.runs[0]!;
  }

  async object(runId: string, id: string): Promise<OntologyObjectContract> {
    this.#assertRun(runId);
    const object = this.#snapshot.objects.find((candidate) => candidate.ref.id === id);
    if (object === undefined) {
      throw new SnapshotDataSourceError(
        "not_available",
        `object ${id} is not available in this snapshot`,
      );
    }
    return object;
  }

  async objects(query: ObjectQuery): Promise<Page<OntologyObjectContract>> {
    this.#assertRun(query.runId);
    const filtered = this.#snapshot.objects.filter(
      (object) =>
        (!query.kinds?.length || query.kinds.includes(object.ref.kind)) &&
        (!query.layers?.length || query.layers.includes(object.layer)),
    );
    return page(filtered, query.limit, query.cursor);
  }

  async relations(query: RelationQuery): Promise<Page<RelationContract>> {
    this.#assertRun(query.runId);
    const direction = query.direction ?? "both";
    const filtered = this.#snapshot.relations.filter((relation) => {
      if (
        query.relationTypes?.length &&
        !query.relationTypes.includes(relation.relation_type)
      ) {
        return false;
      }
      if (!query.incidentIds?.length) {
        return true;
      }
      const source = query.incidentIds.includes(relation.source.id);
      const target = query.incidentIds.includes(relation.target.id);
      return direction === "outgoing"
        ? source
        : direction === "incoming"
          ? target
          : source || target;
    });
    return page(filtered, query.limit, query.cursor);
  }

  async paths(query: PathQuery): Promise<PathResultContract> {
    this.#assertRun(query.runId);
    const maxDepth = query.maxDepth ?? 1;
    const limit = query.limit ?? 20;
    if (maxDepth < 0 || maxDepth > 8 || limit < 1 || limit > 100) {
      throw new SnapshotDataSourceError("query_cost", "snapshot path query exceeds bounds");
    }
    const direction = query.direction ?? "outgoing";
    const relations = this.#snapshot.relations.filter(
      (relation) =>
        !query.relationTypes?.length ||
        query.relationTypes.includes(relation.relation_type),
    );
    const queue: Array<{
      readonly id: string;
      readonly nodes: ReadonlyArray<{ record_type: "ontology_ref"; id: string; kind: string }>;
      readonly relations: ReadonlyArray<RelationContract>;
    }> = [
      {
        id: query.startId,
        nodes: [this.#ref(query.startId)],
        relations: [],
      },
    ];
    const paths: PathContract[] = [];
    let visitedRecords = 0;
    while (queue.length && paths.length < limit) {
      const current = queue.shift()!;
      visitedRecords += 1;
      if (current.id === query.targetId) {
        paths.push({ nodes: current.nodes, relations: current.relations });
        continue;
      }
      if (current.relations.length >= maxDepth) {
        continue;
      }
      for (const relation of relations) {
        const outgoing = relation.source.id === current.id;
        const incoming = relation.target.id === current.id;
        if (
          (direction === "outgoing" && !outgoing) ||
          (direction === "incoming" && !incoming) ||
          (direction === "both" && !outgoing && !incoming)
        ) {
          continue;
        }
        const nextId = outgoing ? relation.target.id : relation.source.id;
        if (current.nodes.some((node) => node.id === nextId)) {
          continue;
        }
        queue.push({
          id: nextId,
          nodes: [...current.nodes, this.#ref(nextId)],
          relations: [...current.relations, relation],
        });
      }
    }
    return { paths, visited_records: visitedRecords, truncated: queue.length > 0 };
  }

  async events(query: EventQuery): Promise<Page<OntologyObjectContract>> {
    this.#assertRun(query.runId);
    return page(orderedEvents(this.#snapshot.objects), query.limit, query.cursor);
  }

  async states(query: EventQuery): Promise<Page<OntologyObjectContract>> {
    this.#assertRun(query.runId);
    return page(
      this.#snapshot.objects.filter((object) => object.ref.kind === "state_observation"),
      query.limit,
      query.cursor,
    );
  }

  async measurements(query: MeasurementQuery): Promise<Page<MeasurementContract>> {
    this.#assertRun(query.runId);
    return page(
      this.#snapshot.measurements.filter(
        (measurement) =>
          (!query.names?.length || query.names.includes(measurement.name)) &&
          (!query.statuses?.length || query.statuses.includes(measurement.status)) &&
          (!query.units?.length || query.units.includes(measurement.unit)),
      ),
      query.limit,
      query.cursor,
    );
  }

  claims(query: ClassificationQuery): Promise<Page<OntologyObjectContract>> {
    return this.#classified(query, "claim");
  }

  evidence(query: ClassificationQuery): Promise<Page<OntologyObjectContract>> {
    return this.#classified(query, "evidence_artifact");
  }

  async ddge(query: EventQuery): Promise<Page<OntologyObjectContract>> {
    this.#assertRun(query.runId);
    return page(
      this.#snapshot.objects.filter((object) =>
        ["ddge_candidate", "ddge_evaluation", "ddge_proposal"].includes(
          object.ref.kind,
        ),
      ),
      query.limit,
      query.cursor,
    );
  }

  async compare(request: ComparisonRequest): Promise<ComparisonResultContract> {
    const comparison = this.#snapshot.comparisons.find(
      (candidate) =>
        candidate.request?.left_run_id === request.left_run_id &&
        candidate.request?.right_run_id === request.right_run_id,
    );
    if (comparison === undefined) {
      throw new SnapshotDataSourceError(
        "not_available",
        "requested comparison was not bundled in this snapshot",
      );
    }
    return comparison;
  }

  #ref(id: string): { record_type: "ontology_ref"; id: string; kind: string } {
    const object = this.#snapshot.objects.find((candidate) => candidate.ref.id === id);
    if (object === undefined) {
      throw new SnapshotDataSourceError(
        "not_available",
        `path object ${id} is not available in this snapshot`,
      );
    }
    return object.ref;
  }

  async #classified(
    query: ClassificationQuery,
    kind: string,
  ): Promise<Page<OntologyObjectContract>> {
    this.#assertRun(query.runId);
    return page(
      this.#snapshot.objects.filter(
        (object) =>
          object.ref.kind === kind &&
          (!query.classifications?.length ||
            (classification(object) !== undefined &&
              query.classifications.includes(classification(object)!))),
      ),
      query.limit,
      query.cursor,
    );
  }
}
