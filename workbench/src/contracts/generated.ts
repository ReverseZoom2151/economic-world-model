// Generated from ewm.workbench.contracts. Do not edit by hand.
export const OPENAPI_SHA256 = "e1972ffe711d91937995d219519139d371fbe3c00bd17bc877a189558e10f892" as const;
export const API_VERSION = "1.0.0" as const;
export const API_PATHS = [
  "/api/v1/claims",
  "/api/v1/comparisons",
  "/api/v1/ddge-candidates",
  "/api/v1/events",
  "/api/v1/evidence",
  "/api/v1/measurements",
  "/api/v1/objects",
  "/api/v1/objects/{object_id}",
  "/api/v1/paths",
  "/api/v1/relations",
  "/api/v1/runs",
  "/api/v1/runs/{run_id}",
  "/api/v1/snapshot-exports",
  "/api/v1/states",
  "/api/v1/system"
] as const;
export type ApiPath = (typeof API_PATHS)[number];

export type ComparisonRequest = { readonly "left_run_id": string; readonly "right_run_id": string; };

export type ErrorDetail = { readonly "code": string; readonly "context"?: { [key: string]: unknown; }; readonly "message": string; };

export type ErrorEnvelope = { readonly "error": ErrorDetail; readonly "ok"?: false; readonly "projection_digests"?: ReadonlyArray<string>; readonly "schema"?: string; };

export type SnapshotExportRequest = { readonly "event_ids"?: ReadonlyArray<string>; readonly "lens"?: string | unknown; readonly "object_ids"?: ReadonlyArray<string>; readonly "relation_ids"?: ReadonlyArray<string>; readonly "run_id": string; };

export type SuccessEnvelope = { readonly "data": unknown; readonly "ok"?: true; readonly "projection_digests"?: ReadonlyArray<string>; readonly "schema"?: string; };
