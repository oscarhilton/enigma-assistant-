import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { EnigmaClient } from "./client";
import { DemoEnigmaClient } from "./DemoEnigmaClient";
import { stitchLlmTrace } from "./forensicDump";
import { MockEnigmaClient } from "./MockEnigmaClient";

const EnigmaClientContext = createContext<EnigmaClient | null>(null);

function resolveClient(): EnigmaClient {
  const mode = import.meta.env.VITE_ENIGMA_MODE as string | undefined;
  if (mode === "demo") {
    return new DemoEnigmaClient();
  }
  return new MockEnigmaClient();
}

export function EnigmaProvider({
  children,
  client,
}: {
  children: ReactNode;
  client?: EnigmaClient;
}) {
  const value = useMemo(() => client ?? resolveClient(), [client]);
  return <EnigmaClientContext.Provider value={value}>{children}</EnigmaClientContext.Provider>;
}

export function useEnigmaClient(): EnigmaClient {
  const client = useContext(EnigmaClientContext);
  if (!client) {
    throw new Error("useEnigmaClient requires EnigmaProvider");
  }
  return client;
}

export function useEnigmaConversation() {
  const client = useEnigmaClient();
  const [items, setItems] = useState<Awaited<ReturnType<EnigmaClient["getConversation"]>>>([]);
  const [attention, setAttention] = useState<Awaited<ReturnType<EnigmaClient["getAttentionState"]>> | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [rows, state] = await Promise.all([client.getConversation(), client.getAttentionState()]);
    setItems(rows);
    setAttention(state);
  }, [client]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void Promise.all([client.getConversation(), client.getAttentionState()])
      .then(([rows, state]) => {
        if (!cancelled) {
          setItems(rows);
          setAttention(state);
        }
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Could not load Enigma");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    const unsub = client.subscribe((event) => {
      if (event.type === "conversation_updated") {
        void client.getConversation().then(setItems);
      }
      if (event.type === "attention_changed" || event.type === "status_changed") {
        void client.getAttentionState().then(setAttention);
        void client.getConversation().then(setItems);
      }
    });
    return () => {
      cancelled = true;
      unsub();
    };
  }, [client]);

  async function sendMessage(text: string) {
    setBusy(true);
    setError(null);
    try {
      const turn = await client.sendMessage(text);
      await refresh();
      setItems((current) => stitchLlmTrace(current, turn.llm_trace ?? turn.debug));
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "Message failed");
      throw cause;
    } finally {
      setBusy(false);
    }
  }

  async function approveAssist(proposalId: string) {
    setBusy(true);
    setError(null);
    try {
      await client.approveAssist(proposalId);
      await refresh();
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "Approval failed");
      throw cause;
    } finally {
      setBusy(false);
    }
  }

  function clearError() {
    setError(null);
  }

  return {
    items,
    attention,
    loading,
    busy,
    error,
    clearError,
    sendMessage,
    approveAssist,
    refresh,
    client,
  };
}
