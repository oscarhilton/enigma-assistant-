import { describe, expect, it } from "vitest";
import {
  BUILD_UNKNOWN_WARNING,
  formatForensicHeader,
  formatTurnBuildLine,
  isBuildIdentityComplete,
} from "./buildIdentity";
import { MOCK_FORENSIC_PROVENANCE } from "./fixtures";

describe("buildIdentity", () => {
  it("formats the forensic header with build, contracts, and runtime", () => {
    const header = formatForensicHeader(MOCK_FORENSIC_PROVENANCE);
    expect(header).not.toContain(BUILD_UNKNOWN_WARNING);
    expect(header).toContain("BUILD");
    expect(header).toContain("NAME              c16-attested-overlay");
    expect(header).toContain("APP VERSION       0.3.0-dev");
    expect(header).toContain("GIT SHA           7c8f4a1");
    expect(header).toContain("BRANCH            ticket/C16-attested-completion");
    expect(header).toContain("DIRTY             true");
    expect(header).toContain("TRACE SCHEMA      2");
    expect(header).toContain("COMPILER          adr029-v3");
    expect(header).toContain("CAPSULE           adr030-c09c-frozen");
    expect(header).toContain("FEATURE FLAGS     c16_overlay,c14_trace_v0");
    expect(header).toContain("ENVIRONMENT       local-demo");
    expect(header).toContain("MODEL             fireworks/gpt-oss-120b");
    expect(header).toContain("WORLD CHECKPOINT  alex-v1@2026-01-19");
    expect(header).toContain("FIXTURE           alex_jan19_continuity_integrity@0.2.1");
  });

  it("shows a conspicuous warning when critical build fields are missing", () => {
    const header = formatForensicHeader({
      build: { name: "unknown", app_version: "0.1.0" },
      contracts: {
        trace_schema: 2,
        compiler: "adr029-v3",
        capsule: "adr030-c09c-frozen",
      },
      runtime: {},
    });
    expect(header).toContain(BUILD_UNKNOWN_WARNING);
    expect(isBuildIdentityComplete({
      build: { name: "unknown", app_version: "0.1.0" },
      contracts: {
        trace_schema: 2,
        compiler: "adr029-v3",
        capsule: "adr030-c09c-frozen",
      },
      runtime: {},
    })).toBe(false);
  });

  it("formats the per-turn compact build line", () => {
    expect(formatTurnBuildLine(MOCK_FORENSIC_PROVENANCE)).toBe(
      "BUILD c16-attested-overlay · 7c8f4a1+dirty.93ad2e\nPROMPT 81e4c9 · TOOLS 42b7a0 · WORLD alex-v1@2026-01-19",
    );
  });
});
