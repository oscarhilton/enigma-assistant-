import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { PrivateWorldClient } from "../pilot/PrivateWorldClient";
import type { WorldId } from "../pilot/types";
import { WorldMockClient } from "../pilot/WorldMockClient";
import { useWorld } from "../pilot/WorldProvider";
import type { EnigmaClient } from "./client";
import { DemoEnigmaClient } from "./DemoEnigmaClient";
import { stitchLlmTrace } from "./forensicDump";
import { isWorldConflictError } from "./readApiJson";

const EnigmaClientContext = createContext<EnigmaClient | null>(null);

type ConversationSession = {
  items: Awaited<ReturnType<EnigmaClient["getConversation"]>>;
  attention: Awaited<ReturnType<EnigmaClient["getAttentionState"]>> | null;
  loading: boolean;
  busy: boolean;
  error: string | null;
  selectedCaseId: string | null;
  selectCase: (id: string | null) => void;
  clearError: () => void;
  sendMessage: (text: string) => Promise<void>;
  approveAssist: (proposalId: string) => Promise<void>;
  refresh: () => Promise<void>;
  client: EnigmaClient;
};

const ConversationContext = createContext<ConversationSession | null>(null);

function resolveClient(world: WorldId): EnigmaClient {
  if (import.meta.env.MODE === "test") {
    return WorldMockClient.forWorld(world);
  }
  if (world === "alex_lab") {
    return new DemoEnigmaClient();
  }
  return new PrivateWorldClient();
}

function useOptionalWorldId(): WorldId {
  try {
    return useWorld().world;
  } catch {
    const mode = import.meta.env.VITE_ENIGMA_MODE as string | undefined;
    return mode === "demo" ? "alex_lab" : "my_enigma";
  }
}

function ConversationHost({
  client,
  children,
}: {
  client: EnigmaClient;
  children: ReactNode;
}) {
  const [items, setItems] = useState<ConversationSession["items"]>([]);
  const [attention, setAttention] = useState<ConversationSession["attention"]>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const loadBlockedRef = useRef(false);

  const refresh = useCallback(async () => {
    if (loadBlockedRef.current) {
      return;
    }
    const [rows, state] = await Promise.all([client.getConversation(), client.getAttentionState()]);
    setItems(rows);
    setAttention(state);
  }, [client]);

  useEffect(() => {
    let cancelled = false;
    loadBlockedRef.current = false;
    setLoading(true);
    setError(null);

    void Promise.all([client.getConversation(), client.getAttentionState()])
      .then(([rows, state]) => {
        if (!cancelled) {
          setItems(rows);
          setAttention(state);
        }
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          const message = cause instanceof Error ? cause.message : "Could not load Enigma";
          if (isWorldConflictError(message)) {
            loadBlockedRef.current = true;
          }
          setError(message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    const safeRefetch = <T,>(run: () => Promise<T>, apply: (value: T) => void) => {
      if (loadBlockedRef.current) {
        return;
      }
      void run()
        .then(apply)
        .catch(() => {
          // Stale demo routes after a world mismatch must not spam 409 loops.
        });
    };

    const unsub = client.subscribe((event) => {
      if (event.type === "conversation_updated") {
        safeRefetch(() => client.getConversation(), setItems);
      }
      if (event.type === "attention_changed" || event.type === "status_changed") {
        safeRefetch(() => client.getAttentionState(), setAttention);
        safeRefetch(() => client.getConversation(), setItems);
      }
    });
    return () => {
      cancelled = true;
      unsub();
    };
  }, [client]);

  const sendMessage = useCallback(
    async (text: string) => {
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
    },
    [client, refresh],
  );

  const approveAssist = useCallback(
    async (proposalId: string) => {
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
    },
    [client, refresh],
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const selectCase = useCallback((id: string | null) => {
    setSelectedCaseId(id);
  }, []);

  const session = useMemo(
    () => ({
      items,
      attention,
      loading,
      busy,
      error,
      selectedCaseId,
      selectCase,
      clearError,
      sendMessage,
      approveAssist,
      refresh,
      client,
    }),
    [
      approveAssist,
      attention,
      busy,
      clearError,
      client,
      error,
      items,
      loading,
      refresh,
      selectCase,
      selectedCaseId,
      sendMessage,
    ],
  );

  return <ConversationContext.Provider value={session}>{children}</ConversationContext.Provider>;
}

export function EnigmaProvider({
  children,
  client,
}: {
  children: ReactNode;
  client?: EnigmaClient;
}) {
  const world = useOptionalWorldId();
  const value = useMemo(() => client ?? resolveClient(world), [client, world]);
  return (
    <EnigmaClientContext.Provider value={value}>
      <ConversationHost client={value}>{children}</ConversationHost>
    </EnigmaClientContext.Provider>
  );
}

export function useEnigmaClient(): EnigmaClient {
  const client = useContext(EnigmaClientContext);
  if (!client) {
    throw new Error("useEnigmaClient requires EnigmaProvider");
  }
  return client;
}

export function useEnigmaConversation(): ConversationSession {
  const session = useContext(ConversationContext);
  if (!session) {
    throw new Error("useEnigmaConversation requires EnigmaProvider");
  }
  return session;
}
