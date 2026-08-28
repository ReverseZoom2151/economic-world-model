export interface WorkbenchBootstrap {
  readonly api_base: "/api/v1";
  readonly api_minor: number;
  readonly session_token: string;
}

let inMemoryBootstrap: WorkbenchBootstrap | null = null;

function decodeBase64Url(value: string): string {
  const base64 = value.replaceAll("-", "+").replaceAll("_", "/");
  return atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, "="));
}

function isBootstrap(value: unknown): value is WorkbenchBootstrap {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.api_base === "/api/v1" &&
    Number.isInteger(candidate.api_minor) &&
    typeof candidate.session_token === "string" &&
    candidate.session_token.length >= 32
  );
}

export function consumeBootstrap(): WorkbenchBootstrap | null {
  const element = document.querySelector<HTMLMetaElement>('meta[name="ewm-bootstrap"]');
  if (element === null) {
    return inMemoryBootstrap;
  }
  const encoded = element.content;
  element.remove();
  try {
    const parsed: unknown = JSON.parse(decodeBase64Url(encoded));
    if (!isBootstrap(parsed)) {
      throw new Error("workbench bootstrap does not match the expected contract");
    }
    inMemoryBootstrap = Object.freeze(parsed);
    return inMemoryBootstrap;
  } catch {
    inMemoryBootstrap = null;
    return null;
  }
}

export function getBootstrap(): WorkbenchBootstrap | null {
  return inMemoryBootstrap;
}
