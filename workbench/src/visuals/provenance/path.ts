export function portableArtifactPath(path: string | null): string {
  if (path === null || path.trim() === "") {
    return "No artifact path recorded";
  }
  const normalized = path.replaceAll("\\", "/");
  if (
    normalized.startsWith("/") ||
    /^[a-zA-Z]:\//.test(normalized) ||
    normalized.split("/").includes("..")
  ) {
    return "[redacted unsafe path]";
  }
  return normalized;
}
