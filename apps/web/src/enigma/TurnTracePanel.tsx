import type { LlmTrace } from "./types";

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function subjectLabel(trace: LlmTrace): string {
  const id = trace.conversation_state.current_subject_id ?? "none";
  const kind = trace.conversation_state.current_subject_kind ?? "none";
  return `${id} (${kind})`;
}

function PrivacySection({ trace }: { trace: LlmTrace }) {
  const disclosure = trace.disclosure;
  const included = disclosure?.included ?? trace.included ?? [];
  const excluded = disclosure?.excluded ?? trace.excluded ?? ["PRIVATE_RAW", "raw email bodies"];
  const remote = Boolean(disclosure) || Boolean(trace.remote_context_sent);

  return (
    <div className="turn-debug-privacy" data-testid="privacy-disclosure-body">
      {remote && disclosure ? (
        <dl>
          <div>
            <dt>Provider</dt>
            <dd>
              {disclosure.provider}/{disclosure.model}
            </dd>
          </div>
          <div>
            <dt>Purpose</dt>
            <dd>{disclosure.purpose}</dd>
          </div>
          <div>
            <dt>Payload hash</dt>
            <dd className="turn-debug-hash">{disclosure.payload_hash}</dd>
          </div>
          {disclosure.blocked ? (
            <div>
              <dt>Blocked</dt>
              <dd>{disclosure.block_reason ?? "yes"}</dd>
            </div>
          ) : null}
        </dl>
      ) : (
        <p className="turn-debug-caption">
          No remote payload — {trace.path === "intent_router" ? "intent_router fallback" : "local planner"}{" "}
          handled this turn.
        </p>
      )}
      <dl>
        <div>
          <dt>Included</dt>
          <dd>{included.length > 0 ? included.join(", ") : "nothing left the machine"}</dd>
        </div>
        <div>
          <dt>Excluded</dt>
          <dd>{excluded.join(", ")}</dd>
        </div>
      </dl>
    </div>
  );
}

export function TurnTracePanel({ trace }: { trace: LlmTrace }) {
  return (
    <div className="turn-debug" data-testid="turn-debug">
      <details className="turn-debug-row" data-testid="llm-trace">
        <summary>LLM trace</summary>
        <dl className="turn-debug-detail">
          <div>
            <dt>Path</dt>
            <dd data-testid="llm-trace-path">{trace.path}</dd>
          </div>
          {trace.correlation_id ? (
            <div>
              <dt>Correlation</dt>
              <dd data-testid="llm-trace-correlation">{trace.correlation_id}</dd>
            </div>
          ) : null}
          <div>
            <dt>USER MESSAGE</dt>
            <dd>{trace.user_message}</dd>
          </div>
          <div>
            <dt>CONVERSATION STATE</dt>
            <dd data-testid="llm-trace-subject">{subjectLabel(trace)}</dd>
          </div>
          {trace.intent_name ? (
            <div>
              <dt>Intent (router)</dt>
              <dd data-testid="llm-trace-intent">{trace.intent_name}</dd>
            </div>
          ) : null}
          <div>
            <dt>TOOLS AVAILABLE</dt>
            <dd>{trace.tools_available.length > 0 ? trace.tools_available.join(", ") : "none"}</dd>
          </div>
          <div>
            <dt>REMOTE CONTEXT SENT</dt>
            <dd>
              {trace.remote_context_sent ? (
                <pre>{formatJson(trace.remote_context_sent)}</pre>
              ) : (
                "none"
              )}
            </dd>
          </div>
          <div>
            <dt>MODEL TOOL REQUEST</dt>
            <dd>
              {trace.model_tool_request.length > 0 ? (
                <pre>{formatJson(trace.model_tool_request)}</pre>
              ) : trace.router_fallback ? (
                "none — router fallback"
              ) : (
                "none"
              )}
            </dd>
          </div>
          {trace.referent_resolution && trace.referent_resolution.length > 0 ? (
            <div>
              <dt>REFERENT RESOLUTION</dt>
              <dd data-testid="llm-trace-referent-resolution">
                <pre>
                  {trace.referent_resolution.map((row) => row.summary).join("\n") ||
                    formatJson(trace.referent_resolution)}
                </pre>
              </dd>
            </div>
          ) : null}
          {trace.executed_tool_request && trace.executed_tool_request.length > 0 ? (
            <div>
              <dt>EXECUTED TOOL REQUEST</dt>
              <dd data-testid="llm-trace-executed-tool-request">
                <pre>{formatJson(trace.executed_tool_request)}</pre>
              </dd>
            </div>
          ) : null}
          <div>
            <dt>TOOL RESULT</dt>
            <dd>
              {trace.tool_results.length > 0 ? <pre>{formatJson(trace.tool_results)}</pre> : "none"}
            </dd>
          </div>
          <div>
            <dt>MODEL RESPONSE</dt>
            <dd>
              {trace.model_response.length > 0 ? (
                <pre>{formatJson(trace.model_response)}</pre>
              ) : (
                "none"
              )}
            </dd>
          </div>
        </dl>
      </details>
      <details className="turn-debug-row" data-testid="privacy-disclosure">
        <summary>Privacy disclosure</summary>
        <PrivacySection trace={trace} />
      </details>
    </div>
  );
}
