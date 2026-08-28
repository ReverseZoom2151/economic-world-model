import { createRoot } from "react-dom/client";

import { App } from "../../src/app/App";
import "../../src/styles/global.css";
import { createFixtureDataSource } from "../../src/testing/fixtures";

const root = document.getElementById("root");
if (root === null) throw new Error("workbench fixture root is missing");

createRoot(root).render(<App dataSource={createFixtureDataSource()} />);
