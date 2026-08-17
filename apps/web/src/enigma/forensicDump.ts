import {
  formatForensicHeader,
  formatTurnBuildLine,
  resolveForensicProvenance,
  type ForensicProvenance,
} from "./buildIdentity";
import type { ConversationItem, LlmTrace } from "./types";

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function subjectLabel(trace: LlmTrace): string {
  const id = trace.conversation_state.current_subject_id ?? "none";
  const kind = trace.conversation_state.current_subject_kind ?? "none";
  return `${id} (${kind})`;
}

function section(label: string, body: string): string {
  return `${label}\n${body}`;
}

function isAssistantItem(item: ConversationItem): boolean {
  return item.kind !== "user_message";
}

function isRunEnd(items: ConversationItem[], index: number): boolean {
  if (!isAssistantItem(items[index]!)) {
    return false;
  }
  const next = items[index + 1];
  return next === undefined || next.kind === "user_message";
}

function traceForRunEndingAt(items: ConversationItem[], endIndex: number): LlmTrace | undefined {
  let start = endIndex;
  while (start > 0 && isAssistantItem(items[start - 1]!)) {
    start -= 1;
  }
  for (let i = start; i <= endIndex; i += 1) {
    const trace = items[i]?.llm_trace;
    if (trace) {
      return trace;
    }
  }
  return undefined;
}

/** One llm_trace per assistant run — same grouping as the under-bonnet panel. */
export function tracesFromItems(items: ConversationItem[]): LlmTrace[] {
  const traces: LlmTrace[] = [];
  for (let i = 0; i < items.length; i += 1) {
    if (!isRunEnd(items, i)) {
      continue;
    }
    const trace = traceForRunEndingAt(items, i);
    if (trace) {
      traces.push(trace);
    }
  }
  return traces;
}

function formatPrivacyDisclosure(trace: LlmTrace): string {
  const disclosure = trace.disclosure;
  const included = disclosure?.included ?? trace.included ?? [];
  const excluded = disclosure?.excluded ?? trace.excluded ?? ["PRIVATE_RAW", "raw email bodies"];
  const remote = Boolean(disclosure) || Boolean(trace.remote_context_sent);
  const parts: string[] = ["Privacy disclosure"];

  if (remote && disclosure) {
    parts.push(section("Provider", `${disclosure.provider}/${disclosure.model}`));
    parts.push(section("Purpose", disclosure.purpose));
    parts.push(section("Payload hash", disclosure.payload_hash));
    if (disclosure.blocked) {
      parts.push(section("Blocked", disclosure.block_reason ?? "yes"));
    }
  } else {
    const handler = trace.path === "intent_router" ? "intent_router fallback" : "local planner";
    parts.push(`No remote payload — ${handler} handled this turn.`);
  }

  parts.push(section("Included", included.length > 0 ? included.join(", ") : "nothing left the machine"));
  parts.push(section("Excluded", excluded.join(", ")));
  return parts.join("\n\n");
}

export type ForensicDumpOptions = {
  provenance?: ForensicProvenance | null;
};

export function formatForensicTurn(
  trace: LlmTrace,
  turnNumber?: number,
  turnCount?: number,
): string {
  const lines: string[] = [];
  if (turnNumber !== undefined) {
    const suffix = turnCount !== undefined ? ` of ${turnCount}` : "";
    lines.push(`======== Turn ${turnNumber}${suffix} ========`);
  }
  const buildLine = formatTurnBuildLine(trace.forensic_provenance);
  if (buildLine) {
    lines.push(buildLine);
  }
  lines.push(section("PATH", trace.path));
  if (trace.correlation_id) {
    lines.push(section("CORRELATION", trace.correlation_id));
  }
  lines.push(section("USER MESSAGE", trace.user_message));
  lines.push(section("CONVERSATION STATE", subjectLabel(trace)));
  if (trace.intent_name) {
    lines.push(section("INTENT", trace.intent_name));
  }
  lines.push(
    section(
      "TOOLS AVAILABLE",
      trace.tools_available.length > 0 ? trace.tools_available.join(", ") : "none",
    ),
  );
  lines.push(
    section(
      "REMOTE CONTEXT SENT",
      trace.remote_context_sent ? formatJson(trace.remote_context_sent) : "none",
    ),
  );

  let toolRequest = "none";
  if (trace.model_tool_request.length > 0) {
    toolRequest = formatJson(trace.model_tool_request);
  } else if (trace.router_fallback) {
    toolRequest = "none — router fallback";
  }
  lines.push(section("MODEL TOOL REQUEST", toolRequest));

  if (trace.referent_resolution && trace.referent_resolution.length > 0) {
    lines.push(
      section(
        "REFERENT RESOLUTION",
        trace.referent_resolution.map((row) => row.summary).join("\n") ||
          formatJson(trace.referent_resolution),
      ),
    );
  }
  if (trace.executed_tool_request && trace.executed_tool_request.length > 0) {
    lines.push(section("EXECUTED TOOL REQUEST", formatJson(trace.executed_tool_request)));
  }
  lines.push(
    section("TOOL RESULT", trace.tool_results.length > 0 ? formatJson(trace.tool_results) : "none"),
  );
  lines.push(
    section(
      "MODEL RESPONSE",
      trace.model_response.length > 0 ? formatJson(trace.model_response) : "none",
    ),
  );
  lines.push(formatPrivacyDisclosure(trace));
  return lines.join("\n\n");
}

const EMPTY_DUMP = "No LLM traces in this conversation yet.";

export function formatSessionDump(traces: LlmTrace[], options?: ForensicDumpOptions): string {
  if (traces.length === 0) {
    return EMPTY_DUMP;
  }
  const provenance = resolveForensicProvenance(traces, options?.provenance);
  const header = formatForensicHeader(provenance);
  const body = traces
    .map((trace, index) => formatForensicTurn(trace, index + 1, traces.length))
    .join("\n\n");
  return `# Enigma forensic dump\nTurns: ${traces.length}\n\n${header}\n\n${body}\n`;
}

export function formatLastTurnDump(traces: LlmTrace[], options?: ForensicDumpOptions): string {
  const last = traces.at(-1);
  if (!last) {
    return EMPTY_DUMP;
  }
  const provenance = resolveForensicProvenance(traces, options?.provenance);
  const header = formatForensicHeader(provenance);
  return `# Enigma forensic dump (last turn)\n\n${header}\n\n${formatForensicTurn(last, traces.length, traces.length)}\n`;
}

/** Local UI memory — attach a turn's llm_trace if GET conversation dropped it. */
export function stitchLlmTrace(
  items: ConversationItem[],
  trace: LlmTrace | undefined,
): ConversationItem[] {
  if (!trace) {
    return items;
  }
  if (
    trace.correlation_id &&
    items.some((item) => item.llm_trace?.correlation_id === trace.correlation_id)
  ) {
    return items;
  }

  let end = items.length - 1;
  while (end >= 0 && items[end]!.kind === "user_message") {
    end -= 1;
  }
  if (end < 0) {
    return items;
  }
  let start = end;
  while (start > 0 && isAssistantItem(items[start - 1]!)) {
    start -= 1;
  }
  if (items.slice(start, end + 1).some((item) => item.llm_trace)) {
    return items;
  }
  const next = items.slice();
  next[start] = { ...next[start]!, llm_trace: trace };
  return next;
}

export async function copyTextToClipboard(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const el = document.createElement("textarea");
  el.value = text;
  el.setAttribute("readonly", "");
  el.style.position = "fixed";
  el.style.left = "-9999px";
  document.body.appendChild(el);
  el.select();
  document.execCommand("copy");
  document.body.removeChild(el);
}
