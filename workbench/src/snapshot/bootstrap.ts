import type { InvestigationSnapshot } from "../data/SnapshotDataSource";
import type { InvestigationState } from "../state/investigation/model";

export class SnapshotIntegrityError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SnapshotIntegrityError";
  }
}

let inMemorySnapshot: InvestigationSnapshot | null = null;

function hex(bytes: ArrayBuffer): string {
  return Array.from(new Uint8Array(bytes), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

function decodeBase64(value: string): Uint8Array<ArrayBuffer> {
  try {
    const decoded = atob(value.trim());
    const bytes = new Uint8Array(decoded.length);
    for (let index = 0; index < decoded.length; index += 1) {
      bytes[index] = decoded.charCodeAt(index);
    }
    return bytes;
  } catch {
    throw new SnapshotIntegrityError("snapshot payload is not valid base64");
  }
}

function isSnapshot(value: unknown): value is InvestigationSnapshot {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Partial<InvestigationSnapshot>;
  return (
    candidate.schema === "ewm.investigation.v1" &&
    typeof candidate.projection_digest === "string" &&
    /^[a-f0-9]{64}$/.test(candidate.projection_digest) &&
    typeof candidate.subset_digest === "string" &&
    /^[a-f0-9]{64}$/.test(candidate.subset_digest) &&
    Array.isArray(candidate.runs) &&
    candidate.runs.length === 1 &&
    Array.isArray(candidate.objects) &&
    Array.isArray(candidate.relations) &&
    Array.isArray(candidate.measurements) &&
    typeof candidate.selection === "object" &&
    candidate.selection !== null
  );
}

export async function consumeSnapshot(): Promise<InvestigationSnapshot | null> {
  const element = document.querySelector<HTMLTemplateElement>("#ewm-snapshot");
  if (element === null) {
    return inMemorySnapshot;
  }
  const declaredDigest = element.dataset.sha256 ?? "";
  const encoded = element.content.textContent ?? "";
  element.remove();
  if (!/^[a-f0-9]{64}$/.test(declaredDigest)) {
    throw new SnapshotIntegrityError("snapshot payload digest is missing or malformed");
  }
  const bytes = decodeBase64(encoded);
  const actualDigest = hex(await crypto.subtle.digest("SHA-256", bytes));
  if (actualDigest !== declaredDigest) {
    throw new SnapshotIntegrityError("snapshot payload failed SHA-256 verification");
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch {
    throw new SnapshotIntegrityError("snapshot payload is not valid UTF-8 JSON");
  }
  if (!isSnapshot(parsed)) {
    throw new SnapshotIntegrityError("snapshot payload does not match ewm.investigation.v1");
  }
  inMemorySnapshot = Object.freeze(parsed);
  return inMemorySnapshot;
}

export function snapshotInvestigationState(
  snapshot: InvestigationSnapshot,
): Partial<InvestigationState> {
  const selection = snapshot.selection;
  return {
    runId: snapshot.runs[0]!.run_id,
    objectId: selection.object_ids[0] ?? null,
    relationId: selection.relation_ids[0] ?? null,
    lens: selection.lens as InvestigationState["lens"],
    timeWindow:
      selection.time_window === null
        ? null
        : { start: selection.time_window.start, end: selection.time_window.end },
    camera: selection.camera,
    filters: {
      kinds: selection.filters.kinds,
      layers: selection.filters.layers,
      query: selection.filters.query,
    },
  };
}
