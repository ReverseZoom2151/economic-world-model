import { beforeEach, describe, expect, it, vi } from "vitest";

function encodedBootstrap(token: string): string {
  return btoa(
    JSON.stringify({
      api_base: "/api/v1",
      api_minor: 0,
      session_token: token,
    }),
  )
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
}

describe("session bootstrap", () => {
  beforeEach(() => {
    vi.resetModules();
    document.head.replaceChildren();
  });

  it("consumes the bootstrap element once and retains it only in module memory", async () => {
    const token = "browser-session-token-with-sufficient-entropy";
    const meta = document.createElement("meta");
    meta.name = "ewm-bootstrap";
    meta.content = encodedBootstrap(token);
    document.head.append(meta);

    const { consumeBootstrap, getBootstrap } = await import(
      "../src/security/bootstrap"
    );
    const bootstrap = consumeBootstrap();

    expect(bootstrap).toEqual({
      api_base: "/api/v1",
      api_minor: 0,
      session_token: token,
    });
    expect(document.querySelector('meta[name="ewm-bootstrap"]')).toBeNull();
    expect(getBootstrap()).toBe(bootstrap);
    expect(consumeBootstrap()).toBe(bootstrap);
  });

  it("removes malformed bootstrap material and fails closed", async () => {
    const meta = document.createElement("meta");
    meta.name = "ewm-bootstrap";
    meta.content = "not-json";
    document.head.append(meta);

    const { consumeBootstrap, getBootstrap } = await import(
      "../src/security/bootstrap"
    );

    expect(consumeBootstrap()).toBeNull();
    expect(getBootstrap()).toBeNull();
    expect(document.querySelector('meta[name="ewm-bootstrap"]')).toBeNull();
  });
});
