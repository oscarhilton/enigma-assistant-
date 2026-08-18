/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      // Demo Mode FastAPI routes (banner, status, environment, timeline,
      // attention, memory, suppressed, why). Same-origin UI fetches need this proxy.
      // Bypass HTML document requests so React Router hard-refresh still
      // works where SPA paths overlap API paths (e.g. /demo/attention).
      "/demo": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        bypass(req) {
          const accept = req.headers.accept;
          const acceptHeader = Array.isArray(accept)
            ? accept.join(",")
            : (accept ?? "");
          if (acceptHeader.includes("text/html")) {
            return "/index.html";
          }
        },
      },
      // Private FastAPI routes (egress disclosures, retention). Without this,
      // same-origin fetch("/private/...") hits Vite's SPA fallback (index.html)
      // and the UI crashes with `Unexpected token '<'`.
      "/private": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        bypass(req) {
          const accept = req.headers.accept;
          const acceptHeader = Array.isArray(accept)
            ? accept.join(",")
            : (accept ?? "");
          if (acceptHeader.includes("text/html")) {
            return "/index.html";
          }
        },
      },
    },
  },
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
