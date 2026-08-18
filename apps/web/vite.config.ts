/// <reference types="vitest/config" />
import { execSync } from "node:child_process";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

function resolveBuildCommit(): string {
  if (process.env.VITE_BUILD_COMMIT) {
    return process.env.VITE_BUILD_COMMIT;
  }
  try {
    return execSync("git rev-parse --short HEAD", { encoding: "utf8" }).trim();
  } catch {
    return "dev";
  }
}

const buildCommit = resolveBuildCommit();

function htmlDocumentBypass(req: { headers: { accept?: string | string[] } }): string | undefined {
  const accept = req.headers.accept;
  const acceptHeader = Array.isArray(accept) ? accept.join(",") : (accept ?? "");
  if (acceptHeader.includes("text/html")) {
    return "/index.html";
  }
  return undefined;
}

export default defineConfig({
  define: {
    "import.meta.env.VITE_BUILD_COMMIT": JSON.stringify(buildCommit),
  },
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
        bypass: htmlDocumentBypass,
      },
      // Private FastAPI routes (egress disclosures, retention). Without this,
      // same-origin fetch("/private/...") hits Vite's SPA fallback (index.html)
      // and the UI crashes with `Unexpected token '<'`.
      "/private": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        bypass: htmlDocumentBypass,
      },
      // Product worlds (My Enigma conversation, switcher). v2 and pilot fetch same-origin.
      "/worlds": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        bypass: htmlDocumentBypass,
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
