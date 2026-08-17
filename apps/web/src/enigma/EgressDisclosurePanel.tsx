import { useEffect, useState } from "react";
import type { EnigmaClient } from "./client";
import {
  DisclosureUnavailableError,
  disclosureErrorFromUnknown,
} from "./disclosureFetch";
import type { CompiledTurnManifest, EgressDisclosure } from "./types";

type Props = {
  client: EnigmaClient;
};

type PayloadTab = "summary" | "exact" | "trace";

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function includedModules(manifest: CompiledTurnManifest): string[] {
  return Object.entries(manifest.context)
    .filter(([, decision]) => decision.include)
    .map(([name]) => name);
}

function excludedModules(manifest: CompiledTurnManifest): string[] {
  return Object.entries(manifest.context)
    .filter(([, decision]) => !decision.include)
    .map(([name]) => name);
}

function toolNamesFromPayload(payload: Record<string, unknown> | null | undefined): string[] {
  const tools = payload?.tools;
  if (!Array.isArray(tools)) {
    return [];
  }
  const names: string[] = [];
  for (const tool of tools) {
    if (tool && typeof tool === "object" && "function" in tool) {
      const fn = (tool as { function?: { name?: unknown } }).function;
      if (fn && typeof fn.name === "string" && fn.name) {
        names.push(fn.name);
      }
    }
  }
  return names;
}

function providerLabel(disclosure: EgressDisclosure): string {
  const provider = disclosure.provider;
  const pretty = provider === "fireworks" ? "Fireworks" : provider;
  return `${pretty} / ${disclosure.model}`;
}

function DisclosureRow({ disclosure }: { disclosure: EgressDisclosure }) {
  const [tab, setTab] = useState<PayloadTab>("summary");
  const statusLabel = disclosure.blocked ? "Blocked" : "Sent";
  const statusClass = disclosure.blocked ? "egress-disclosure-status-blocked" : "egress-disclosure-status-sent";
  const permitted = toolNamesFromPayload(disclosure.outbound_payload);
  const summaryNames = Array.isArray(disclosure.payload_field_summary.tool_names)
    ? (disclosure.payload_field_summary.tool_names as string[])
    : [];
  const displayedTools = permitted.length > 0 ? permitted : summaryNames;
  const included = disclosure.included ?? [];
  const excluded = disclosure.excluded ?? [];
  const denied = disclosure.denied_capabilities ?? [];
  const actions = disclosure.enigma_actions ?? [];
  const toolTrace = disclosure.tool_trace ?? [];

  return (
    <details className="egress-disclosure-row" data-testid={`disclosure-${disclosure.id}`}>
      <summary>
        <span className="egress-disclosure-time">{formatTimestamp(disclosure.timestamp)}</span>
        <span className="egress-disclosure-purpose">{disclosure.purpose}</span>
        <span className="egress-disclosure-provider">{providerLabel(disclosure)}</span>
        <span className={`egress-disclosure-status ${statusClass}`}>{statusLabel}</span>
      </summary>
      <div className="egress-disclosure-detail">
        <dl>
          <div>
            <dt>Correlation</dt>
            <dd data-testid={`disclosure-corr-${disclosure.id}`}>{disclosure.correlation_id}</dd>
          </div>
          <div>
            <dt>Transformation</dt>
            <dd>{disclosure.transformation_profile}</dd>
          </div>
          <div>
            <dt>Classification</dt>
            <dd>{disclosure.classification}</dd>
          </div>
          <div>
            <dt>Payload hash</dt>
            <dd className="egress-disclosure-hash">{disclosure.payload_hash}</dd>
          </div>
          <div>
            <dt>Byte count</dt>
            <dd>{disclosure.byte_count.toLocaleString()}</dd>
          </div>
          {disclosure.blocked && disclosure.block_reason ? (
            <div>
              <dt>Block reason</dt>
              <dd>{disclosure.block_reason}</dd>
            </div>
          ) : null}
          {!disclosure.blocked ? (
            <div>
              <dt>Tokens</dt>
              <dd>
                {disclosure.prompt_tokens} prompt · {disclosure.completion_tokens} completion
              </dd>
            </div>
          ) : null}
        </dl>

        <div className="egress-disclosure-payload">
          <div className="egress-disclosure-tabs" role="tablist" aria-label="Inspect exact payload">
            <button
              type="button"
              role="tab"
              aria-selected={tab === "summary"}
              className={tab === "summary" ? "is-active" : undefined}
              onClick={() => setTab("summary")}
            >
              Summary
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === "exact"}
              className={tab === "exact" ? "is-active" : undefined}
              onClick={() => setTab("exact")}
            >
              Exact outbound payload
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === "trace"}
              className={tab === "trace" ? "is-active" : undefined}
              onClick={() => setTab("trace")}
            >
              Tool trace
            </button>
          </div>

          {tab === "summary" ? (
            <div className="egress-disclosure-tab-body" data-testid="disclosure-tab-summary">
              <p className="egress-disclosure-caption">
                No raw source content was included. Email bodies, calendar descriptions, contact
                details and private world records were not transmitted.
              </p>
              <dl className="egress-disclosure-forensic">
                <div>
                  <dt>What left?</dt>
                  <dd>Transformed remote-safe payload (see Exact outbound payload).</dd>
                </div>
                <div>
                  <dt>Why?</dt>
                  <dd>{disclosure.purpose}</dd>
                </div>
                <div>
                  <dt>Who received it?</dt>
                  <dd>
                    {providerLabel(disclosure)}
                    {disclosure.transport_endpoint ? (
                      <span className="egress-disclosure-endpoint">
                        {" "}
                        · {disclosure.transport_endpoint}
                      </span>
                    ) : null}
                  </dd>
                </div>
                <div>
                  <dt>What authority did it have?</dt>
                  <dd>
                    <p>Model could request: {displayedTools.length > 0 ? displayedTools.join(", ") : "none"}</p>
                    <p>Model could NOT request: {denied.length > 0 ? denied.join(", ") : "none listed"}</p>
                  </dd>
                </div>
                <div>
                  <dt>What came back?</dt>
                  <dd>
                    {toolTrace.length > 0
                      ? toolTrace
                          .map((hop) => hop.request?.name ?? hop.result?.name ?? "tool")
                          .join(", ")
                      : "no tool request"}
                  </dd>
                </div>
                <div>
                  <dt>What did Enigma actually do?</dt>
                  <dd>
                    {actions.length > 0
                      ? actions
                          .map((action) => {
                            const side = action.side_effect ? "side effect" : "no side effect";
                            return `${action.name}: ${action.effect} (${side})`;
                          })
                          .join("; ")
                      : "no side effect"}
                  </dd>
                </div>
                <div>
                  <dt>Included</dt>
                  <dd>{included.length > 0 ? included.join(", ") : "none"}</dd>
                </div>
                <div>
                  <dt>Excluded</dt>
                  <dd>{excluded.length > 0 ? excluded.join(", ") : "none"}</dd>
                </div>
              </dl>
              {disclosure.context_manifest ? (
                <div data-testid="disclosure-context-manifest">
                  <p className="egress-disclosure-caption">
                    Compiled-turn manifest — why each included context earned its place. Not the
                    prompt.
                  </p>
                  <dl className="egress-disclosure-forensic">
                    <div>
                      <dt>Request profile</dt>
                      <dd>{disclosure.context_manifest.profile}</dd>
                    </div>
                    {disclosure.context_manifest.speech_act ? (
                      <div>
                        <dt>Speech act</dt>
                        <dd>{disclosure.context_manifest.speech_act}</dd>
                      </div>
                    ) : null}
                    <div>
                      <dt>Included modules</dt>
                      <dd>
                        {includedModules(disclosure.context_manifest).join(", ") || "none"}
                      </dd>
                    </div>
                    <div>
                      <dt>Excluded modules</dt>
                      <dd>
                        {excludedModules(disclosure.context_manifest).join(", ") || "none"}
                      </dd>
                    </div>
                    <div>
                      <dt>Permitted tools</dt>
                      <dd>
                        {disclosure.context_manifest.tools.length > 0
                          ? disclosure.context_manifest.tools.join(", ")
                          : "none"}
                      </dd>
                    </div>
                  </dl>
                  <pre data-testid="disclosure-context-manifest-json">
                    {formatJson(disclosure.context_manifest)}
                  </pre>
                </div>
              ) : null}
              <pre>{formatJson(disclosure.payload_field_summary)}</pre>
            </div>
          ) : null}

          {tab === "exact" ? (
            <div className="egress-disclosure-tab-body" data-testid="disclosure-tab-exact">
              <p className="egress-disclosure-caption">
                Actual JSON handed to the provider after transformation. Transport secrets (API key)
                are stripped.
              </p>
              <pre data-testid="disclosure-outbound-payload">
                {formatJson(disclosure.outbound_payload ?? {})}
              </pre>
            </div>
          ) : null}

          {tab === "trace" ? (
            <div className="egress-disclosure-tab-body" data-testid="disclosure-tab-trace">
              <p className="egress-disclosure-caption">
                End-to-end tool request and completion for correlation {disclosure.correlation_id}.
              </p>
              <pre data-testid="disclosure-tool-trace">
                {formatJson({
                  correlation_id: disclosure.correlation_id,
                  provider_response: disclosure.provider_response ?? null,
                  tool_trace: toolTrace,
                  enigma_actions: actions,
                })}
              </pre>
            </div>
          ) : null}
        </div>
      </div>
    </details>
  );
}

function DisclosureErrorView({ error }: { error: DisclosureUnavailableError }) {
  return (
    <div className="egress-disclosure-error" data-testid="egress-disclosure-error" role="alert">
      <p className="egress-disclosure-error-title">Privacy disclosure unavailable</p>
      <p>Expected {error.expected}</p>
      <p>Received {error.received}</p>
      <p>HTTP {error.status}</p>
      <p>Endpoint: {error.endpoint}</p>
      <p>Correlation: {error.correlationId}</p>
      {error.preview ? (
        <p className="egress-disclosure-error-preview" data-testid="egress-disclosure-error-preview">
          {error.preview}
        </p>
      ) : null}
    </div>
  );
}

export function EgressDisclosurePanel({ client }: Props) {
  const [open, setOpen] = useState(false);
  const [disclosures, setDisclosures] = useState<EgressDisclosure[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<DisclosureUnavailableError | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    void client
      .getRecentDisclosures()
      .then((rows) => {
        if (!cancelled) {
          setDisclosures(Array.isArray(rows) ? rows : []);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(disclosureErrorFromUnknown(err));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [client, open]);

  return (
    <div className="egress-disclosure" data-testid="egress-disclosure-panel">
      <button
        type="button"
        className="egress-disclosure-toggle"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        What left my machine?
      </button>
      {open ? (
        <section className="egress-disclosure-panel" aria-label="Recent egress disclosures">
          <header className="egress-disclosure-header">
            <h2>What left my machine?</h2>
            <p>Falsifiable privacy boundary — audited remote inference disclosures only.</p>
          </header>
          {loading ? <p className="egress-disclosure-caption">Loading disclosures…</p> : null}
          {error ? <DisclosureErrorView error={error} /> : null}
          {!loading && !error && disclosures.length === 0 ? (
            <p className="egress-disclosure-caption" data-testid="egress-disclosure-empty">
              No remote inference disclosures yet.
            </p>
          ) : null}
          {!loading && disclosures.length > 0 ? (
            <div className="egress-disclosure-list">
              {disclosures.map((disclosure) => (
                <DisclosureRow key={disclosure.id} disclosure={disclosure} />
              ))}
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
