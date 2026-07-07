import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { defineConfig } from "vitest/config";

import { pwaOptions } from "./src/pwa/pwaConfig";

// Vite build config.
//
// The SPA is served SAME-ORIGIN by FastAPI under the `/app` URL prefix
// (see frontend/spa_serving.py). `base: "/app/"` makes Vite emit asset URLs
// as `/app/assets/<name>-<hash>.js`, matching the FastAPI static mount.
//
// Node is BUILD-TIME ONLY: this produces static files in `dist/`; no Node
// process runs in production.
//
// PWA (Phase 4): `VitePWA` generates the Workbox service worker
// (`dist/sw.js`), the web app manifest (`dist/manifest.webmanifest`) and the
// external registration script (`dist/registerSW.js`). Its caching strategy —
// and the mandatory architect-council conditions on it — live in and are
// unit-tested from `src/pwa/pwaConfig.ts`. FastAPI serves those root-level
// build artifacts at `/app/*` (frontend/spa_serving.py) so the SW (at
// `/app/sw.js`) controls exactly the `/app` scope.
export default defineConfig({
  plugins: [react(), VitePWA(pwaOptions)],
  base: "/app/",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // Emit dist/.vite/manifest.json so the Vite -> FastAPI asset contract can
    // be resolved programmatically if a later increment needs it. FastAPI
    // currently serves Vite's generated index.html verbatim (which already
    // references the hashed assets), so no hashed filename is hardcoded in
    // Python.
    manifest: true,
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
