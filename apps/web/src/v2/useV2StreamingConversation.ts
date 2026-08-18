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

/**
 * Cancel semantics (UI2-02): Stop generating response ≠ cancel underlying work.
 * Stop aborts fetch/prose only; AgentWork keeps the last `agent_work` snapshot.
 * Server emits nothing on client abort — we do not fabricate idle/complete.
 * GET conversation (refresh) reconciles durable state after Stop or drop.
 */
export function useV2StreamingConversation(): V2StreamingConversation {
  const { world } = useWorld();
  const session = useEnigmaConversation();
  const [items, setItems] = useState<ConversationItem[]>(session.items);
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
    setItems(session.items);
  }, [session.items]);

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
      if (world !== "my_enigma") {
        await session.sendMessage(text);
        return true;
      }
      setBusy(true);
      setDisconnected(false);
      setGenerationStopped(false);
      setError(null);
      setStreamingText("");
      turnCompleteRef.current = false;
      lastTextRef.current = text;
      const pending: ConversationItem = {
        kind: "user_message",
        text,
        at: new Date().toISOString(),
      };
      setItems((current) => [...current, pending]);
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
            if (event.type === "agent_work") {
              setAgentWork(event.data);
            } else if (event.type === "prose") {
              setStreamingText((current) => current + event.data.delta);
            } else if (event.type === "turn_complete") {
              turnCompleteRef.current = true;
              setItems((current) => {
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
    [session, world],
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
