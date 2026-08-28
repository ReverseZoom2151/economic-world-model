import { resolve } from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  build: {
    assetsDir: "assets",
    emptyOutDir: true,
    manifest: "manifest.json",
    outDir: resolve(import.meta.dirname, "../src/ewm/workbench/static"),
    rollupOptions: {
      output: {
        assetFileNames: "assets/[name]-[hash][extname]",
        chunkFileNames: "assets/[name]-[hash].js",
        entryFileNames: "assets/[name]-[hash].js",
      },
    },
    sourcemap: false,
    target: "es2022",
  },
  plugins: [react()],
  publicDir: false,
});
