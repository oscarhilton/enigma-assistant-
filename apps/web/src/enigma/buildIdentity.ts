export type BuildIdentity = {
  name: string;
  app_version: string;
  git_sha?: string | null;
  branch?: string | null;
  dirty?: boolean;
  patch_hash?: string | null;
  build_fingerprint?: string | null;
};

export type ForensicContracts = {
  trace_schema: number;
  compiler: string;
  capsule: string;
  prompt_bundle?: string | null;
  tool_registry?: string | null;
  feature_flags?: string[];
};

export type ForensicRuntime = {
  environment?: string | null;
  session_started?: string | null;
  model?: string | null;
  world_checkpoint?: string | null;
  fixture?: string | null;
};

export type ForensicProvenance = {
  build: BuildIdentity;
  contracts: ForensicContracts;
  runtime: ForensicRuntime;
};

export const BUILD_UNKNOWN_WARNING = "BUILD UNKNOWN — FORENSIC COMPARISON UNSAFE";

export function shortHash(value: string | null | undefined, length = 6): string {
  if (!value) {
    return "??????";
  }
  const digest = value.startsWith("sha256:") ? value.slice("sha256:".length) : value;
  return digest.slice(0, length);
}

export function isBuildIdentityComplete(provenance: ForensicProvenance | null | undefined): boolean {
  if (!provenance) {
    return false;
  }
  const { build, contracts } = provenance;
  const critical = [
    build.name,
    build.app_version,
    build.git_sha,
    build.build_fingerprint,
    contracts.prompt_bundle,
    contracts.tool_registry,
  ];
  return critical.every((value) => Boolean(value) && value !== "unknown");
}

function padLabel(label: string, width = 18): string {
  return `${label}`.padEnd(width);
}

function formatBuildSha(build: BuildIdentity): string {
  const sha = build.git_sha ?? "???????";
  if (!build.dirty) {
    return sha;
  }
  return `${sha}+dirty.${shortHash(build.patch_hash)}`;
}

export function formatTurnBuildLine(provenance: ForensicProvenance | null | undefined): string | null {
  if (!provenance) {
    return null;
  }
  const { build, contracts, runtime } = provenance;
  const buildPart = `BUILD ${build.name} · ${formatBuildSha(build)}`;
  const promptPart = `PROMPT ${shortHash(contracts.prompt_bundle)}`;
  const toolsPart = `TOOLS ${shortHash(contracts.tool_registry)}`;
  const worldPart = runtime.world_checkpoint ? ` · WORLD ${runtime.world_checkpoint}` : "";
  return `${buildPart}\n${promptPart} · ${toolsPart}${worldPart}`;
}

export function formatForensicHeader(provenance: ForensicProvenance | null | undefined): string {
  const lines: string[] = [];
  if (!isBuildIdentityComplete(provenance)) {
    lines.push(BUILD_UNKNOWN_WARNING);
    lines.push("");
  }
  if (!provenance) {
    return lines.join("\n");
  }

  const { build, contracts, runtime } = provenance;
  lines.push("BUILD");
  lines.push(`${padLabel("NAME")}${build.name}`);
  lines.push(`${padLabel("APP VERSION")}${build.app_version}`);
  lines.push(`${padLabel("GIT SHA")}${build.git_sha ?? "unknown"}`);
  lines.push(`${padLabel("BRANCH")}${build.branch ?? "unknown"}`);
  lines.push(`${padLabel("DIRTY")}${String(Boolean(build.dirty))}`);
  lines.push(`${padLabel("PATCH HASH")}${build.patch_hash ?? "unknown"}`);
  lines.push(`${padLabel("BUILD FINGERPRINT")}${build.build_fingerprint ?? "unknown"}`);
  lines.push("");
  lines.push("CONTRACTS");
  lines.push(`${padLabel("TRACE SCHEMA")}${contracts.trace_schema}`);
  lines.push(`${padLabel("COMPILER")}${contracts.compiler}`);
  lines.push(`${padLabel("CAPSULE")}${contracts.capsule}`);
  lines.push(`${padLabel("PROMPT BUNDLE")}${contracts.prompt_bundle ?? "unknown"}`);
  lines.push(`${padLabel("TOOL REGISTRY")}${contracts.tool_registry ?? "unknown"}`);
  lines.push(`${padLabel("FEATURE FLAGS")}${(contracts.feature_flags ?? []).join(",")}`);
  lines.push("");
  lines.push("RUNTIME");
  lines.push(`${padLabel("ENVIRONMENT")}${runtime.environment ?? "unknown"}`);
  lines.push(`${padLabel("SESSION STARTED")}${runtime.session_started ?? "unknown"}`);
  lines.push(`${padLabel("MODEL")}${runtime.model ?? "unknown"}`);
  lines.push(`${padLabel("WORLD CHECKPOINT")}${runtime.world_checkpoint ?? "unknown"}`);
  lines.push(`${padLabel("FIXTURE")}${runtime.fixture ?? "unknown"}`);
  return lines.join("\n");
}

export function resolveForensicProvenance(
  traces: { forensic_provenance?: ForensicProvenance | null }[],
  explicit?: ForensicProvenance | null,
): ForensicProvenance | null {
  if (explicit) {
    return explicit;
  }
  for (const trace of traces) {
    if (trace.forensic_provenance) {
      return trace.forensic_provenance;
    }
  }
  return null;
}
