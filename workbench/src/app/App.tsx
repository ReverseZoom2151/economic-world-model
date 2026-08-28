import { useMemo } from "react";

import { AppShell } from "../components/AppShell";
import { ApiDataSource } from "../data/ApiDataSource";
import type {
  InvestigationDataSource,
  RunSummary,
  SystemContract,
} from "../data/InvestigationDataSource";
import { getBootstrap } from "../security/bootstrap";
import { InvestigationProvider } from "../state/investigation";
import type { InvestigationState } from "../state/investigation/model";

class LauncherRequiredDataSource implements InvestigationDataSource {
  async system(): Promise<SystemContract> {
    return {
      api_major: 1,
      api_minor: 0,
      mode: "client-only",
      run_count: 0,
      status: "unsupported",
    };
  }

  async runs(): Promise<ReadonlyArray<RunSummary>> {
    return [];
  }

  run = rejected;
  object = rejected;
  objects = rejected;
  relations = rejected;
  paths = rejected;
  events = rejected;
  states = rejected;
  measurements = rejected;
  claims = rejected;
  evidence = rejected;
  ddge = rejected;
  compare = rejected;
}

function rejected(): Promise<never> {
  return Promise.reject(new Error("start the client through the local workbench launcher"));
}

function browserDataSource(): InvestigationDataSource {
  const bootstrap = getBootstrap();
  return bootstrap === null
    ? new LauncherRequiredDataSource()
    : new ApiDataSource(bootstrap);
}

interface AppProps {
  readonly dataSource?: InvestigationDataSource;
  readonly initialState?: Partial<InvestigationState>;
}

export function App({ dataSource, initialState }: AppProps) {
  const source = useMemo(() => dataSource ?? browserDataSource(), [dataSource]);
  return (
    <InvestigationProvider initialState={initialState}>
      <AppShell dataSource={source} />
    </InvestigationProvider>
  );
}
