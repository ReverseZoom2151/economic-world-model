export const INVESTIGATION_LENSES = [
  "world",
  "runtime",
  "market",
  "learning",
  "ddge",
  "compare",
  "evidence",
  "lineage",
  "scene",
  "globe",
] as const;

export type InvestigationLens = (typeof INVESTIGATION_LENSES)[number];

export interface TimeWindow {
  readonly start: number;
  readonly end: number;
}

export interface RunComparison {
  readonly leftRunId: string;
  readonly rightRunId: string;
}

export interface CameraState {
  readonly projection: "perspective" | "orthographic";
  readonly position: readonly [number, number, number];
  readonly target: readonly [number, number, number];
}

export interface InvestigationFilters {
  readonly kinds: ReadonlyArray<string>;
  readonly layers: ReadonlyArray<string>;
  readonly query: string;
}

export interface InvestigationState {
  readonly runId: string | null;
  readonly objectId: string | null;
  readonly relationId: string | null;
  readonly timeWindow: TimeWindow | null;
  readonly comparison: RunComparison | null;
  readonly lens: InvestigationLens;
  readonly camera: CameraState | null;
  readonly filters: InvestigationFilters;
}

export const initialInvestigationState: InvestigationState = Object.freeze({
  runId: null,
  objectId: null,
  relationId: null,
  timeWindow: null,
  comparison: null,
  lens: "world",
  camera: null,
  filters: Object.freeze({ kinds: [], layers: [], query: "" }),
});

type HydratedState = Partial<InvestigationState>;

export type InvestigationAction =
  | { readonly type: "select-run"; readonly runId: string | null }
  | { readonly type: "select-object"; readonly objectId: string | null }
  | { readonly type: "select-relation"; readonly relationId: string | null }
  | { readonly type: "set-time-window"; readonly window: TimeWindow | null }
  | { readonly type: "set-comparison"; readonly comparison: RunComparison | null }
  | { readonly type: "set-lens"; readonly lens: InvestigationLens }
  | { readonly type: "set-camera"; readonly camera: CameraState | null }
  | { readonly type: "set-filters"; readonly filters: InvestigationFilters }
  | { readonly type: "hydrate"; readonly state: HydratedState };

function normalizedWindow(window: TimeWindow | null): TimeWindow | null {
  if (window === null) {
    return null;
  }
  return window.start <= window.end
    ? { start: window.start, end: window.end }
    : { start: window.end, end: window.start };
}

export function investigationReducer(
  state: InvestigationState,
  action: InvestigationAction,
): InvestigationState {
  switch (action.type) {
    case "select-run":
      return action.runId === state.runId
        ? state
        : {
            ...state,
            runId: action.runId,
            objectId: null,
            relationId: null,
            timeWindow: null,
          };
    case "select-object":
      return { ...state, objectId: action.objectId };
    case "select-relation":
      return { ...state, relationId: action.relationId };
    case "set-time-window":
      return { ...state, timeWindow: normalizedWindow(action.window) };
    case "set-comparison":
      return { ...state, comparison: action.comparison };
    case "set-lens":
      return { ...state, lens: action.lens };
    case "set-camera":
      return { ...state, camera: action.camera };
    case "set-filters":
      return {
        ...state,
        filters: {
          kinds: [...new Set(action.filters.kinds)].sort(),
          layers: [...new Set(action.filters.layers)].sort(),
          query: action.filters.query,
        },
      };
    case "hydrate":
      return {
        ...state,
        ...action.state,
        timeWindow: normalizedWindow(action.state.timeWindow ?? state.timeWindow),
        filters: action.state.filters ?? state.filters,
      };
  }
}

function finiteNumber(value: string | null): number | null {
  if (value === null || value.trim() === "") {
    return null;
  }
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function isLens(value: string | null): value is InvestigationLens {
  return value !== null && (INVESTIGATION_LENSES as readonly string[]).includes(value);
}

function textList(value: string | null): ReadonlyArray<string> {
  return value === null
    ? []
    : [...new Set(value.split(",").map((item) => item.trim()).filter(Boolean))].sort();
}

function parseCamera(value: string | null): CameraState | null {
  if (value === null) {
    return null;
  }
  const [projection, ...coordinates] = value.split(",");
  const numbers = coordinates.map((coordinate) => finiteNumber(coordinate));
  if (
    (projection !== "perspective" && projection !== "orthographic") ||
    numbers.length !== 6 ||
    numbers.some((coordinate) => coordinate === null)
  ) {
    return null;
  }
  const [x, y, z, targetX, targetY, targetZ] = numbers as [
    number,
    number,
    number,
    number,
    number,
    number,
  ];
  return {
    projection,
    position: [x, y, z],
    target: [targetX, targetY, targetZ],
  };
}

function cameraValue(camera: CameraState | null): string | null {
  return camera === null
    ? null
    : [camera.projection, ...camera.position, ...camera.target].join(",");
}

export function parseInvestigationUrl(search: string): HydratedState {
  const parameters = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const start = finiteNumber(parameters.get("from"));
  const end = finiteNumber(parameters.get("to"));
  const lens = parameters.get("lens");
  const leftRunId = parameters.get("left");
  const rightRunId = parameters.get("right");
  const camera = parseCamera(parameters.get("camera"));
  return {
    runId: parameters.get("run"),
    objectId: parameters.get("object"),
    relationId: parameters.get("relation"),
    ...(isLens(lens) ? { lens } : {}),
    ...(start !== null && end !== null
      ? { timeWindow: normalizedWindow({ start, end }) }
      : {}),
    ...(leftRunId !== null && rightRunId !== null
      ? { comparison: { leftRunId, rightRunId } }
      : {}),
    ...(camera === null ? {} : { camera }),
    filters: {
      kinds: textList(parameters.get("kinds")),
      layers: textList(parameters.get("layers")),
      query: parameters.get("q") ?? "",
    },
  };
}

export function serializeInvestigationUrl(state: InvestigationState): string {
  const parameters = new URLSearchParams();
  const values: ReadonlyArray<readonly [string, string | null]> = [
    ["run", state.runId],
    ["object", state.objectId],
    ["relation", state.relationId],
    ["lens", state.lens],
    ["from", state.timeWindow === null ? null : String(state.timeWindow.start)],
    ["to", state.timeWindow === null ? null : String(state.timeWindow.end)],
    ["left", state.comparison?.leftRunId ?? null],
    ["right", state.comparison?.rightRunId ?? null],
    ["camera", cameraValue(state.camera)],
    ["kinds", state.filters.kinds.length ? state.filters.kinds.join(",") : null],
    ["layers", state.filters.layers.length ? state.filters.layers.join(",") : null],
    ["q", state.filters.query || null],
  ];
  for (const [key, value] of values) {
    if (value !== null) {
      parameters.set(key, value);
    }
  }
  const query = parameters.toString();
  return query ? `?${query}` : "";
}
