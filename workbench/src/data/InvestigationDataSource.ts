import type { ComparisonRequest } from "../contracts/generated";

export type WorkbenchStatus =
  | "ready"
  | "partial"
  | "unsupported"
  | "integrity_error";

export interface SystemContract {
  readonly api_major: number;
  readonly api_minor: number;
  readonly run_count: number;
  readonly mode: string;
  readonly status?: WorkbenchStatus;
}

export interface RunSummary {
  readonly run_id: string;
  readonly source_run_hash: string;
  readonly profile_identity: string;
  readonly integrity_level: string;
  readonly projection_digest: string;
  readonly ontology_schema: string;
  readonly coverage?: ReadonlyArray<CoverageContract>;
}

export interface CoverageContract {
  readonly record_type: "coverage_entry";
  readonly source: SourceLocatorContract;
  readonly field: string;
  readonly status: string;
  readonly targets: ReadonlyArray<OntologyRefContract>;
  readonly reason: string | null;
}

export interface OntologyRefContract {
  readonly record_type: "ontology_ref";
  readonly id: string;
  readonly kind: string;
}

export interface SourceLocatorContract {
  readonly record_type: "source_locator";
  readonly source_kind: string;
  readonly source_id: string;
  readonly artifact_path: string | null;
  readonly record_selector: string | null;
  readonly code_symbol: string | null;
  readonly paper_anchor: string | null;
  readonly payload_digest: string | null;
}

export interface OntologyObjectContract {
  readonly record_type: "ontology_object";
  readonly ref: OntologyRefContract;
  readonly layer: string;
  readonly properties: Readonly<Record<string, unknown>>;
  readonly sources: ReadonlyArray<SourceLocatorContract>;
}

export interface RelationContract {
  readonly record_type: "relation_assertion";
  readonly ref: OntologyRefContract;
  readonly relation_type: string;
  readonly source: OntologyRefContract;
  readonly target: OntologyRefContract;
  readonly properties: Readonly<Record<string, unknown>>;
  readonly sources: ReadonlyArray<SourceLocatorContract>;
}

export interface MeasurementContract {
  readonly record_type: "measurement";
  readonly ref: OntologyRefContract;
  readonly subject: OntologyRefContract;
  readonly name: string;
  readonly value: unknown;
  readonly unit: string;
  readonly status: string;
  readonly sample: Readonly<Record<string, unknown>>;
  readonly uncertainty: Readonly<Record<string, unknown>>;
  readonly sources: ReadonlyArray<SourceLocatorContract>;
}

export interface Page<T> {
  readonly items: ReadonlyArray<T>;
  readonly next_cursor: string | null;
}

export interface ObjectQuery {
  readonly runId: string;
  readonly kinds?: ReadonlyArray<string>;
  readonly layers?: ReadonlyArray<string>;
  readonly limit?: number;
  readonly cursor?: string;
}

export interface RelationQuery {
  readonly runId: string;
  readonly relationTypes?: ReadonlyArray<string>;
  readonly incidentIds?: ReadonlyArray<string>;
  readonly direction?: "outgoing" | "incoming" | "both";
  readonly limit?: number;
  readonly cursor?: string;
}

export interface PathQuery {
  readonly runId: string;
  readonly startId: string;
  readonly targetId: string;
  readonly maxDepth?: number;
  readonly limit?: number;
  readonly relationTypes?: ReadonlyArray<string>;
  readonly direction?: "outgoing" | "incoming" | "both";
}

export interface EventQuery {
  readonly runId: string;
  readonly limit?: number;
  readonly cursor?: string;
}

export interface MeasurementQuery extends EventQuery {
  readonly names?: ReadonlyArray<string>;
  readonly statuses?: ReadonlyArray<string>;
  readonly units?: ReadonlyArray<string>;
}

export interface ClassificationQuery extends EventQuery {
  readonly classifications?: ReadonlyArray<string>;
}

export interface ComparisonResultContract {
  readonly comparison_id: string;
  readonly request?: Readonly<Record<string, unknown>>;
  readonly result: Readonly<Record<string, unknown>>;
}

export interface PathResultContract {
  readonly paths: ReadonlyArray<Readonly<Record<string, unknown>>>;
  readonly visited_records: number;
  readonly truncated: boolean;
}

export interface InvestigationDataSource {
  system(): Promise<SystemContract>;
  runs(): Promise<ReadonlyArray<RunSummary>>;
  run(id: string): Promise<RunSummary>;
  object(runId: string, id: string): Promise<OntologyObjectContract>;
  objects(query: ObjectQuery): Promise<Page<OntologyObjectContract>>;
  relations(query: RelationQuery): Promise<Page<RelationContract>>;
  paths(query: PathQuery): Promise<PathResultContract>;
  events(query: EventQuery): Promise<Page<OntologyObjectContract>>;
  states(query: EventQuery): Promise<Page<OntologyObjectContract>>;
  measurements(query: MeasurementQuery): Promise<Page<MeasurementContract>>;
  claims(query: ClassificationQuery): Promise<Page<OntologyObjectContract>>;
  evidence(query: ClassificationQuery): Promise<Page<OntologyObjectContract>>;
  ddge(query: EventQuery): Promise<Page<OntologyObjectContract>>;
  compare(request: ComparisonRequest): Promise<ComparisonResultContract>;
}
