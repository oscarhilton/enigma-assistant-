import type { EnigmaEventHandler } from "./events";
import type { EnigmaClient } from "./client";
import {
  DISCLOSURE_RECENT_PATH,
  disclosureErrorFromUnknown,
  newDisclosureCorrelationId,
  readDisclosureList,
} from "./disclosureFetch";
import type {
  AssistProposal,
  AssistResult,
  AttentionState,
  ConversationItem,
  ConversationTurn,
  DemoEvent,
  EgressDisclosure,
  ProvenanceView,
  QualificationDebug,
} from "./types";
import type { DemoStatus } from "./client";

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

const LOCAL_API_TOKEN =
  (import.meta.env.VITE_ENIGMA_API_TOKEN as string | undefined) ?? "local-dev-token";

async function readJson<T>(response: Response): Promise<T> {
  const url = response.url || "(unknown url)";
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${url}`);
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`API returned HTML / not JSON (${response.status}) ${url}`);
  }
}

export class DemoEnigmaClient implements EnigmaClient {
  private handlers = new Set<EnigmaEventHandler>();

  isDemo(): boolean {
    return true;
  }

  subscribe(handler: EnigmaEventHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  private emit(event: Parameters<EnigmaEventHandler>[0]): void {
    for (const handler of this.handlers) {
      handler(event);
    }
  }

  async getConversation(): Promise<ConversationItem[]> {
    const body = await readJson<{ items: ConversationItem[] }>(
      await fetch(`${API_BASE}/demo/conversation`),
    );
    return body.items;
  }

  async sendMessage(text: string): Promise<ConversationTurn> {
    const body = await readJson<ConversationTurn>(
      await fetch(`${API_BASE}/demo/conversation/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      }),
    );
    this.emit({ type: "conversation_updated" });
    return body;
  }

  async getAttentionState(): Promise<AttentionState> {
    return readJson<AttentionState>(await fetch(`${API_BASE}/demo/attention/state`));
  }

  async getQualificationDebug(itemId: string): Promise<QualificationDebug> {
    return readJson<QualificationDebug>(
      await fetch(`${API_BASE}/demo/attention/${itemId}/qualification-debug`),
    );
  }

  async getProvenance(itemId: string): Promise<ProvenanceView> {
    const body = await readJson<{
      item_id: string;
      title: string;
      headline: string;
      evidence: string[];
      inference: string[];
      decision: string[];
      why_now: string[];
      reason_codes: string[];
    }>(await fetch(`${API_BASE}/demo/why/${itemId}`));
    return {
      item_id: body.item_id,
      headline: body.headline,
      evidence: body.evidence,
      inference: body.inference,
      decision: body.decision,
      why_now: body.why_now,
      reason_codes: body.reason_codes,
    };
  }

  async proposeAssist(intent: string): Promise<AssistProposal> {
    const turn = await this.sendMessage(intent);
    const item = turn.items.find((row) => row.kind === "assist_proposal");
    if (item?.kind !== "assist_proposal") {
      throw new Error("Demo did not return an assist proposal");
    }
    return item.proposal;
  }

  async approveAssist(proposalId: string): Promise<AssistResult> {
    const body = await readJson<{ ok: boolean; message: string }>(
      await fetch(`${API_BASE}/demo/assist/${proposalId}/approve`, { method: "POST" }),
    );
    this.emit({ type: "conversation_updated" });
    this.emit({ type: "status_changed" });
    return { ok: body.ok, message: body.message };
  }

  async jumpCheckpoint(checkpointId: string): Promise<void> {
    const body = await readJson<{ events?: DemoEvent[]; checkpoint_id: string }>(
      await fetch(`${API_BASE}/demo/timeline/checkpoint/${checkpointId}`, { method: "POST" }),
    );
    this.emit({ type: "attention_changed", checkpoint_id: body.checkpoint_id });
    const last = body.events?.at(-1);
    if (last) {
      this.emit({ type: "demo_event", event: last });
    }
    this.emit({ type: "status_changed" });
  }

  async listCheckpoints(): Promise<{ id: string; at: string; label: string }[]> {
    const body = await readJson<{ checkpoints: { id: string; at: string; label: string }[] }>(
      await fetch(`${API_BASE}/demo/checkpoints`),
    );
    return body.checkpoints;
  }

  async getDemoEvents(): Promise<DemoEvent[]> {
    const body = await readJson<{ events: DemoEvent[] }>(await fetch(`${API_BASE}/demo/events`));
    return body.events;
  }

  async getDemoStatus(): Promise<DemoStatus> {
    return readJson<DemoStatus>(await fetch(`${API_BASE}/demo/status`));
  }

  async advanceDemoDay(): Promise<void> {
    await readJson(await fetch(`${API_BASE}/demo/timeline/day`, { method: "POST" }));
    this.emit({ type: "status_changed" });
  }

  async advanceDemoStep(): Promise<void> {
    await readJson(await fetch(`${API_BASE}/demo/timeline/step`, { method: "POST" }));
    this.emit({ type: "status_changed" });
  }

  async setDemoSpeed(speed: number): Promise<void> {
    await readJson(
      await fetch(`${API_BASE}/demo/timeline/speed`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ speed }),
      }),
    );
    this.emit({ type: "status_changed" });
  }

  async getRecentDisclosures(limit = 20): Promise<EgressDisclosure[]> {
    const endpoint = DISCLOSURE_RECENT_PATH;
    const correlationId = newDisclosureCorrelationId();
    try {
      const response = await fetch(`${API_BASE}${endpoint}?limit=${limit}`, {
        headers: {
          Authorization: `Bearer ${LOCAL_API_TOKEN}`,
          Accept: "application/json",
          "X-Correlation-Id": correlationId,
        },
      });
      return await readDisclosureList(response, { endpoint, correlationId });
    } catch (err) {
      throw disclosureErrorFromUnknown(err, correlationId);
    }
  }
}
