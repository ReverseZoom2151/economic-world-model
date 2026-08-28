import type { ComparisonRequest } from "../contracts/generated";
import type { WorkbenchBootstrap } from "../security/bootstrap";
import type {
  ClassificationQuery,
  ComparisonResultContract,
  EventQuery,
  InvestigationDataSource,
  MeasurementContract,
  MeasurementQuery,
  ObjectQuery,
  OntologyObjectContract,
  Page,
  PathQuery,
  PathResultContract,
  RelationContract,
  RelationQuery,
  RunSummary,
  SystemContract,
} from "./InvestigationDataSource";

interface ApiEnvelope<T> {
  readonly ok: boolean;
  readonly schema: string;
  readonly projection_digests: ReadonlyArray<string>;
  readonly data?: T;
  readonly error?: {
    readonly code: string;
    readonly message: string;
    readonly context: Readonly<Record<string, unknown>>;
  };
}

export class DataSourceError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = "DataSourceError";
    this.code = code;
    this.status = status;
  }
}

export class IntegrityDataError extends DataSourceError {
  constructor(message: string, status: number) {
    super("integrity_failed", message, status);
    this.name = "IntegrityDataError";
  }
}

function appendQuery(
  path: string,
  values: Readonly<Record<string, string | number | ReadonlyArray<string> | undefined>>,
): string {
  const parameters = new URLSearchParams();
  for (const [key, rawValue] of Object.entries(values).sort(([left], [right]) =>
    left.localeCompare(right),
  )) {
    if (rawValue === undefined) {
      continue;
    }
    parameters.set(key, Array.isArray(rawValue) ? rawValue.join(",") : String(rawValue));
  }
  const query = parameters.toString();
  return query ? `${path}?${query}` : path;
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(canonicalJson).join(",")}]`;
  }
  if (typeof value === "object" && value !== null) {
    const record = value as Readonly<Record<string, unknown>>;
    return `{${Object.keys(record)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(record[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value) ?? "null";
}

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function asEnvelope<T>(value: unknown): ApiEnvelope<T> {
  if (typeof value !== "object" || value === null) {
    throw new DataSourceError("invalid_response", "API response is not an object", 502);
  }
  const envelope = value as Partial<ApiEnvelope<T>>;
  if (
    typeof envelope.ok !== "boolean" ||
    envelope.schema !== "ewm.workbench.api.v1" ||
    !Array.isArray(envelope.projection_digests)
  ) {
    throw new DataSourceError(
      "invalid_response",
      "API response does not match ewm.workbench.api.v1",
      502,
    );
  }
  return envelope as ApiEnvelope<T>;
}

export class ApiDataSource implements InvestigationDataSource {
  readonly #apiBase: string;
  readonly #apiMinor: number;
  readonly #sessionToken: string;
  readonly #fetcher: typeof fetch;

  constructor(bootstrap: WorkbenchBootstrap, fetcher: typeof fetch = globalThis.fetch) {
    this.#apiBase = bootstrap.api_base;
    this.#apiMinor = bootstrap.api_minor;
    this.#sessionToken = bootstrap.session_token;
    this.#fetcher = fetcher;
  }

  async #request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await this.#fetcher(`${this.#apiBase}${path}`, {
      ...init,
      cache: "no-store",
      credentials: "omit",
      headers: {
        Accept: "application/json",
        "X-EWM-Token": this.#sessionToken,
        ...init.headers,
      },
      redirect: "error",
    });
    const receivedMinor = Number(response.headers.get("X-EWM-API-Minor"));
    if (!Number.isInteger(receivedMinor) || receivedMinor < this.#apiMinor) {
      throw new DataSourceError(
        "api_version_mismatch",
        "API minor version is older than the client contract",
        response.status,
      );
    }
    let decoded: unknown;
    try {
      decoded = await response.json();
    } catch {
      throw new DataSourceError(
        "invalid_response",
        "API response is not valid JSON",
        response.status,
      );
    }
    const envelope = asEnvelope<T>(decoded);
    if (!response.ok || !envelope.ok || envelope.data === undefined) {
      const code = envelope.error?.code ?? "request_failed";
      const message = envelope.error?.message ?? "workbench request failed";
      if (code === "integrity_failed") {
        throw new IntegrityDataError(message, response.status);
      }
      throw new DataSourceError(code, message, response.status);
    }
    return envelope.data;
  }

  system(): Promise<SystemContract> {
    return this.#request("/system");
  }

  async runs(): Promise<ReadonlyArray<RunSummary>> {
    const page = await this.#request<{ readonly items: ReadonlyArray<RunSummary> }>("/runs");
    return page.items;
  }

  run(id: string): Promise<RunSummary> {
    return this.#request(`/runs/${encodeURIComponent(id)}`);
  }

  object(runId: string, id: string): Promise<OntologyObjectContract> {
    return this.#request(
      appendQuery(`/objects/${encodeURIComponent(id)}`, { run_id: runId }),
    );
  }

  objects(query: ObjectQuery): Promise<Page<OntologyObjectContract>> {
    return this.#request(
      appendQuery("/objects", {
        cursor: query.cursor,
        kinds: query.kinds,
        layers: query.layers,
        limit: query.limit,
        run_id: query.runId,
      }),
    );
  }

  relations(query: RelationQuery): Promise<Page<RelationContract>> {
    return this.#request(
      appendQuery("/relations", {
        cursor: query.cursor,
        direction: query.direction,
        incident_ids: query.incidentIds,
        limit: query.limit,
        relation_types: query.relationTypes,
        run_id: query.runId,
      }),
    );
  }

  paths(query: PathQuery): Promise<PathResultContract> {
    return this.#request(
      appendQuery("/paths", {
        direction: query.direction,
        limit: query.limit,
        max_depth: query.maxDepth,
        relation_types: query.relationTypes,
        run_id: query.runId,
        start_id: query.startId,
        target_id: query.targetId,
      }),
    );
  }

  events(query: EventQuery): Promise<Page<OntologyObjectContract>> {
    return this.#eventPage("/events", query);
  }

  states(query: EventQuery): Promise<Page<OntologyObjectContract>> {
    return this.#eventPage("/states", query);
  }

  measurements(query: MeasurementQuery): Promise<Page<MeasurementContract>> {
    return this.#request(
      appendQuery("/measurements", {
        cursor: query.cursor,
        limit: query.limit,
        names: query.names,
        run_id: query.runId,
        statuses: query.statuses,
        units: query.units,
      }),
    );
  }

  claims(query: ClassificationQuery): Promise<Page<OntologyObjectContract>> {
    return this.#classificationPage("/claims", query);
  }

  evidence(query: ClassificationQuery): Promise<Page<OntologyObjectContract>> {
    return this.#classificationPage("/evidence", query);
  }

  ddge(query: EventQuery): Promise<Page<OntologyObjectContract>> {
    return this.#eventPage("/ddge-candidates", query);
  }

  async compare(request: ComparisonRequest): Promise<ComparisonResultContract> {
    const body = canonicalJson(request);
    const idempotencyKey = `ewm-${await sha256(body)}`;
    return this.#request("/comparisons", {
      body,
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
      },
      method: "POST",
    });
  }

  #eventPage(
    path: string,
    query: EventQuery,
  ): Promise<Page<OntologyObjectContract>> {
    return this.#request(
      appendQuery(path, {
        cursor: query.cursor,
        limit: query.limit,
        run_id: query.runId,
      }),
    );
  }

  #classificationPage(
    path: string,
    query: ClassificationQuery,
  ): Promise<Page<OntologyObjectContract>> {
    return this.#request(
      appendQuery(path, {
        classifications: query.classifications,
        cursor: query.cursor,
        limit: query.limit,
        run_id: query.runId,
      }),
    );
  }
}
