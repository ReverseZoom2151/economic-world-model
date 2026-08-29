import type { RunSummary } from "../../data/InvestigationDataSource";

export function profileLabel(value: string): string {
  const tokens = value.split(/[._-]/).filter((token) => token.toLowerCase() !== "ewm");
  const version = tokens.at(-1)?.match(/^v\d+$/i) ? (tokens.pop() ?? null) : null;
  const words = tokens.map((token, index) => {
    const upper = token.toUpperCase();
    if (["FX", "DDGE", "EWM"].includes(upper)) return upper;
    return index === 0
      ? `${token[0]?.toUpperCase() ?? ""}${token.slice(1)}`
      : token.toLowerCase();
  });
  const base = words.join(" ") || "Economic";
  return `${base} model${version === null ? "" : ` · ${version}`}`;
}

export function runLabel(run: RunSummary, index: number): string {
  return `${profileLabel(run.profile_identity)} · run ${index + 1}`;
}
