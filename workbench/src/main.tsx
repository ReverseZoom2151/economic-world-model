import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";
import { consumeBootstrap } from "./security/bootstrap";
import "./styles/global.css";

consumeBootstrap();

const root = document.getElementById("root");
if (root === null) {
  throw new Error("workbench root element is missing");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
