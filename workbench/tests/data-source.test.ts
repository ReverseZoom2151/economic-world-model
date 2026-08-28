import { describe, expect, it, vi } from "vitest";

import { ApiDataSource, IntegrityDataError } from "../src/data/ApiDataSource";

const bootstrap = {
  api_base: "/api/v1" as const,
  api_minor: 0,
  session_token: "data-source-session-token-with-sufficient-entropy",
};

function envelope(data: unknown, status = 200): Response {
  return new Response(
    JSON.stringify({
      ok: status < 400,
      schema: "ewm.workbench.api.v1",
      projection_digests: [],
      ...(status < 400
        ? { data }
        : {
            error: {
              code: "integrity_failed",
              message: "projection verification failed",
              context: {},
            },
          }),
    }),
    {
      status,
      headers: {
        "Content-Type": "application/json",
        "X-EWM-API-Minor": "0",
      },
    },
  );
}

describe("ApiDataSource", () => {
  it("keeps credentials in headers while mapping versioned envelopes", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      envelope({
        items: [
          {
            run_id: "run-a",
            source_run_hash: "a".repeat(20),
            profile_identity: "ewm.scalar.v1",
            integrity_level: "checksummed",
            projection_digest: "b".repeat(64),
            ontology_schema: "ewm.ontology.v1",
          },
        ],
      }),
    );
    const source = new ApiDataSource(bootstrap, fetcher);

    const runs = await source.runs();

    expect(runs).toHaveLength(1);
    expect(runs[0]?.run_id).toBe("run-a");
    const [url, options] = fetcher.mock.calls[0] ?? [];
    expect(String(url)).toBe("/api/v1/runs");
    expect(String(url)).not.toContain(bootstrap.session_token);
    expect(new Headers(options?.headers).get("X-EWM-Token")).toBe(
      bootstrap.session_token,
    );
    expect(options?.credentials).toBe("omit");
    expect(options?.cache).toBe("no-store");
  });

  it("serializes bounded queries and canonical comparison commands", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        envelope({ items: [], next_cursor: null }),
      )
      .mockResolvedValueOnce(envelope({ comparison_id: "comparison", result: {} }));
    const source = new ApiDataSource(bootstrap, fetcher);

    await source.objects({
      runId: "run-a",
      kinds: ["agent", "market"],
      layers: ["economic_declaration"],
      limit: 25,
    });
    await source.compare({ left_run_id: "run-a", right_run_id: "run-b" });

    expect(String(fetcher.mock.calls[0]?.[0])).toBe(
      "/api/v1/objects?kinds=agent%2Cmarket&layers=economic_declaration&limit=25&run_id=run-a",
    );
    const comparison = fetcher.mock.calls[1];
    expect(String(comparison?.[0])).toBe("/api/v1/comparisons");
    expect(comparison?.[1]?.method).toBe("POST");
    expect(new Headers(comparison?.[1]?.headers).get("Idempotency-Key")).toMatch(
      /^ewm-[a-f0-9]{64}$/,
    );
  });

  it("preserves integrity failures as a distinct client state", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(envelope(null, 409));
    const source = new ApiDataSource(bootstrap, fetcher);

    await expect(source.runs()).rejects.toBeInstanceOf(IntegrityDataError);
  });
});
