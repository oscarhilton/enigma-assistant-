import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { ConversationItem } from "../enigma/types";
import { useWorld } from "../pilot/WorldProvider";
import {
  loadActiveThreadId,
  loadThreads,
  saveActiveThreadId,
  saveThreads,
} from "./threadStorage";
import { createThread, NEW_CHAT_TITLE, threadTitleFromMessage, type V2Thread } from "./threadTypes";

type V2ThreadContextValue = {
  threads: V2Thread[];
  activeThread: V2Thread;
  activeThreadId: string;
  selectThread: (threadId: string) => void;
  createNewThread: () => void;
  updateActiveThreadItems: (items: ConversationItem[]) => void;
  renameActiveThreadFromMessage: (text: string) => void;
};

const V2ThreadContext = createContext<V2ThreadContextValue | null>(null);

export function V2ThreadProvider({ children }: { children: ReactNode }) {
  const { world } = useWorld();
  const [state, setState] = useState(() => {
    const loaded = loadThreads(world);
    return {
      threads: loaded,
      activeThreadId: loadActiveThreadId(world, loaded),
    };
  });
  const { threads, activeThreadId } = state;

  const persist = useCallback(
    (nextThreads: V2Thread[], nextActiveId: string) => {
      saveThreads(world, nextThreads);
      saveActiveThreadId(world, nextActiveId);
    },
    [world],
  );

  const activeThread = useMemo(
    () => threads.find((thread) => thread.id === activeThreadId) ?? threads[0] ?? createThread(),
    [activeThreadId, threads],
  );

  const selectThread = useCallback(
    (threadId: string) => {
      if (!threads.some((thread) => thread.id === threadId)) {
        return;
      }
      setState((current) => ({ ...current, activeThreadId: threadId }));
      saveActiveThreadId(world, threadId);
    },
    [threads, world],
  );

  const createNewThread = useCallback(() => {
    const thread = createThread();
    const nextThreads = [thread, ...threads];
    setState({ threads: nextThreads, activeThreadId: thread.id });
    persist(nextThreads, thread.id);
  }, [persist, threads]);

  const updateActiveThreadItems = useCallback(
    (items: ConversationItem[]) => {
      const now = new Date().toISOString();
      setState((current) => {
        const nextThreads = current.threads.map((thread) =>
          thread.id === current.activeThreadId ? { ...thread, items, updatedAt: now } : thread,
        );
        saveThreads(world, nextThreads);
        return { ...current, threads: nextThreads };
      });
    },
    [world],
  );

  const renameActiveThreadFromMessage = useCallback(
    (text: string) => {
      setState((current) => {
        const nextThreads = current.threads.map((thread) => {
          if (thread.id !== current.activeThreadId || thread.title !== NEW_CHAT_TITLE) {
            return thread;
          }
          return { ...thread, title: threadTitleFromMessage(text), updatedAt: new Date().toISOString() };
        });
        saveThreads(world, nextThreads);
        return { ...current, threads: nextThreads };
      });
    },
    [world],
  );

  const value = useMemo(
    () => ({
      threads,
      activeThread,
      activeThreadId,
      selectThread,
      createNewThread,
      updateActiveThreadItems,
      renameActiveThreadFromMessage,
    }),
    [
      activeThread,
      activeThreadId,
      createNewThread,
      renameActiveThreadFromMessage,
      selectThread,
      threads,
      updateActiveThreadItems,
    ],
  );

  return <V2ThreadContext.Provider value={value}>{children}</V2ThreadContext.Provider>;
}

export function useV2Threads(): V2ThreadContextValue {
  const context = useContext(V2ThreadContext);
  if (!context) {
    throw new Error("useV2Threads requires V2ThreadProvider");
  }
  return context;
}
