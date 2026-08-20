import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useEnigmaConversation } from "../enigma/EnigmaProvider";
import {
  licenceFromConversation,
  type AgentWorkSnapshot,
  type GoosePixelLicence,
} from "../enigma/goosePixels";
import type { ConversationItem } from "../enigma/types";
import { useWorld } from "../pilot/WorldProvider";
import { streamConversationMessage } from "./conversationStreamClient";
import { gooseFromAgentWork } from "./gooseFromAgentWork";
import { useStreamTrace } from "./StreamTraceProvider";
import type { CapturedStreamEvent } from "./streamTrace";
import type { ConversationStreamEvent } from "./streamTypes";
import { appendStreamingText, type V2MessageRow } from "./V2ConversationViewport";

export type V2StreamingConversation = {
  items: ConversationItem[];
  streamingRow: V2MessageRow | null;
  streamingText: string;
  loading: boolean;
  busy: boolean;
  error: string | null;
  disconnected: boolean;
  /** True after Stop — prose aborted; AgentWork unchanged. */
  generationStopped: boolean;
  gooseLicence: GoosePixelLicence;
  client: ReturnType<typeof useEnigmaConversation>["client"];
  sendMessage: (text: string) => Promise<boolean>;
  cancel: () => void;
  reconnect: () => Promise<void>;
  clearError: () => void;
};

type ThreadCallbacks = {
  threadItems: ConversationItem[];
  onThreadItemsChange: (items: ConversationItem[]) => void;
  onFirstMessage?: (text: string) => void;
};

/**
 * Cancel semantics (UI2-02): Stop generating response ≠ cancel underlying work.
 * Stop aborts fetch/prose only; AgentWork keeps the last `agent_work` snapshot.
 * Server emits nothing on client abort — we do not fabricate idle/complete.
 * GET conversation (refresh) reconciles durable state after Stop or drop.
 */
export function useV2StreamingConversation(threadCallbacks?: ThreadCallbacks): V2StreamingConversation {
  const { world } = useWorld();
  const session = useEnigmaConversation();
  const { beginForensicTurn, captureStreamEvents } = useStreamTrace();
  const threadItems = threadCallbacks?.threadItems;
  const onThreadItemsChange = threadCallbacks?.onThreadItemsChange;
  const onFirstMessage = threadCallbacks?.onFirstMessage;
  const [items, setItems] = useState<ConversationItem[]>(threadItems ?? session.items);
  const [streamingText, setStreamingText] = useState("");
  const [agentWork, setAgentWork] = useState<AgentWorkSnapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const [disconnected, setDisconnected] = useState(false);
  const [generationStopped, setGenerationStopped] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const lastTextRef = useRef<string | null>(null);
  const turnCompleteRef = useRef(false);

  useEffect(() => {
    if (threadItems) {
      setItems(threadItems);
    }
  }, [threadItems]);

  // Seed empty local thread from server conversation (C34 bootstrap expressiveness).
  useEffect(() => {
    if (!threadItems || !onThreadItemsChange || session.loading) {
      return;
    }
    if (threadItems.length === 0 && session.items.length > 0) {
      queueMicrotask(() => onThreadItemsChange(session.items));
    }
  }, [onThreadItemsChange, session.items, session.loading, threadItems]);

  // Alex Lab checkpoints replace conversation wholesale — mirror session into the active thread.
  useEffect(() => {
    if (world === "my_enigma" || !threadItems || !onThreadItemsChange || session.loading) {
      return;
    }
    if (JSON.stringify(threadItems) !== JSON.stringify(session.items)) {
      queueMicrotask(() => onThreadItemsChange(session.items));
    }
  }, [onThreadItemsChange, session.items, session.loading, threadItems, world]);

  useEffect(() => {
    if (threadItems) {
      return;
    }
    setItems(session.items);
  }, [session.items, threadItems]);

  const commitItems = useCallback(
    (next: ConversationItem[] | ((current: ConversationItem[]) => ConversationItem[])) => {
      setItems((current) => {
        const resolved = typeof next === "function" ? next(current) : next;
        if (onThreadItemsChange) {
          queueMicrotask(() => onThreadItemsChange(resolved));
        }
        return resolved;
      });
    },
    [onThreadItemsChange],
  );

  const streamingRow = useMemo(
    () => (streamingText ? appendStreamingText(null, streamingText) : null),
    [streamingText],
  );

  const gooseLicence = useMemo(() => {
    if (agentWork?.exists) {
      return gooseFromAgentWork(agentWork, items);
    }
    return licenceFromConversation({
      items,
      busy: world !== "my_enigma" && (session.busy || busy),
      loading: session.loading,
    });
  }, [agentWork, busy, items, session.busy, session.loading, world]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const cancel = useCallback(() => {
    // Abort prose/fetch only — AgentWork is not cleared here.
    abortRef.current?.abort();
  }, []);

  const sendMessage = useCallback(
    async (text: string): Promise<boolean> => {
      onFirstMessage?.(text);
      if (world !== "my_enigma") {
        await session.sendMessage(text);
        const rows = await session.client.getConversation();
        commitItems(rows);
        return true;
      }
      setBusy(true);
      setDisconnected(false);
      setGenerationStopped(false);
      setError(null);
      setStreamingText("");
      turnCompleteRef.current = false;
      lastTextRef.current = text;
      const captured: CapturedStreamEvent[] = [];
      const sentAt = new Date().toISOString();
      const pending: ConversationItem = {
        kind: "user_message",
        text,
        at: sentAt,
      };
      beginForensicTurn({ text, at: sentAt });
      commitItems((current) => [...current, pending]);
      setAgentWork({
        exists: true,
        phase: "in_flight",
        semanticToken: "in-flight",
        inspectTarget: null,
        inspectLabels: [],
      });
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const outcome = await streamConversationMessage(text, {
          signal: controller.signal,
          onEvent: (event) => {
            captured.push({ capturedAt: Date.now(), event });
            captureStreamEvents(captured);
            if (event.type === "agent_work") {
              setAgentWork(event.data);
            } else if (event.type === "prose") {
              setStreamingText((current) => current + event.data.delta);
            } else if (event.type === "turn_complete") {
              turnCompleteRef.current = true;
              commitItems((current) => {
                if (event.data.conversation?.items) {
                  return event.data.conversation.items;
                }
                const withoutPending = current.filter((item) => item !== pending);
                return [...withoutPending, pending, ...event.data.items];
              });
              setStreamingText("");
            } else if (event.type === "error") {
              setError(event.data.message);
            }
          },
        });
        if (outcome === "aborted") {
          setStreamingText("");
          setGenerationStopped(true);
          // Retain agentWork — last server snapshot stays for Goose.
          try {
            await session.refresh();
          } catch {
            /* Reconnect can retry refresh */
          }
          return false;
        }
        if (outcome === "disconnected") {
          setDisconnected(true);
          return false;
        }
        return turnCompleteRef.current;
      } finally {
        setBusy(false);
        abortRef.current = null;
      }
    },
    [beginForensicTurn, captureStreamEvents, commitItems, onFirstMessage, session, world],
  );

  const reconnect = useCallback(async () => {
    setDisconnected(false);
    setError(null);
    setGenerationStopped(false);
    try {
      await session.refresh();
    } catch {
      setDisconnected(true);
      return;
    }
    if (lastTextRef.current && !turnCompleteRef.current) {
      await sendMessage(lastTextRef.current);
    }
  }, [sendMessage, session]);

  return {
    items,
    streamingRow,
    streamingText,
    loading: session.loading,
    busy: busy || (world !== "my_enigma" && session.busy),
    error: error ?? session.error,
    disconnected,
    generationStopped,
    gooseLicence,
    client: session.client,
    sendMessage,
    cancel,
    reconnect,
    clearError,
  };
}
