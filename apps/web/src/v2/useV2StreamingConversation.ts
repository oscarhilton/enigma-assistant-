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
  gooseLicence: GoosePixelLicence;
  client: ReturnType<typeof useEnigmaConversation>["client"];
  sendMessage: (text: string) => Promise<boolean>;
  cancel: () => void;
  reconnect: () => Promise<void>;
  clearError: () => void;
};

export function useV2StreamingConversation(): V2StreamingConversation {
  const { world } = useWorld();
  const session = useEnigmaConversation();
  const [items, setItems] = useState<ConversationItem[]>(session.items);
  const [streamingText, setStreamingText] = useState("");
  const [agentWork, setAgentWork] = useState<AgentWorkSnapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const [disconnected, setDisconnected] = useState(false);
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
          setAgentWork(null);
          setItems((current) => current.filter((item) => item !== pending));
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
    gooseLicence,
    client: session.client,
    sendMessage,
    cancel,
    reconnect,
    clearError,
  };
}
