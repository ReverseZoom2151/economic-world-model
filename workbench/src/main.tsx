import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";
import { SnapshotDataSource } from "./data/SnapshotDataSource";
import { consumeBootstrap } from "./security/bootstrap";
import {
  consumeSnapshot,
  snapshotInvestigationState,
} from "./snapshot/bootstrap";
import "./styles/global.css";

const root = document.getElementById("root");
if (root === null) {
  throw new Error("workbench root element is missing");
}

async function start(): Promise<void> {
  try {
    const snapshot = await consumeSnapshot();
    consumeBootstrap();
    const dataSource =
      snapshot === null ? undefined : new SnapshotDataSource(snapshot);
    const initialState =
      snapshot === null ? undefined : snapshotInvestigationState(snapshot);
    createRoot(root!).render(
      <StrictMode>
        <App dataSource={dataSource} initialState={initialState} />
      </StrictMode>,
    );
  } catch (error) {
    root!.dataset.snapshotIntegrity = "failed";
    root!.setAttribute("role", "alert");
    root!.textContent =
      error instanceof Error
        ? `Snapshot integrity check failed: ${error.message}`
        : "Snapshot integrity check failed.";
  }
}

void start();
