import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import {
  bindForensicTurn,
  type ForensicTurnBinding,
  type ForensicUserInput,
} from "./debug/forensicTurn";
import { projectStreamTrace, type CapturedStreamEvent, type StreamingTraceProjection } from "./streamTrace";

type StreamTraceContextValue = {
  lastTrace: StreamingTraceProjection | null;
  forensicTurn: ForensicTurnBinding | null;
  beginForensicTurn: (userInput: ForensicUserInput) => void;
  captureStreamEvents: (events: CapturedStreamEvent[]) => void;
};

const StreamTraceContext = createContext<StreamTraceContextValue>({
  lastTrace: null,
  forensicTurn: null,
  beginForensicTurn: () => undefined,
  captureStreamEvents: () => undefined,
});

export function StreamTraceProvider({ children }: { children: ReactNode }) {
  const [lastTrace, setLastTrace] = useState<StreamingTraceProjection | null>(null);
  const [forensicTurn, setForensicTurn] = useState<ForensicTurnBinding | null>(null);
  const provisionalUserInputRef = useRef<ForensicUserInput | null>(null);

  const beginForensicTurn = useCallback((userInput: ForensicUserInput) => {
    provisionalUserInputRef.current = userInput;
    setForensicTurn(null);
    setLastTrace(null);
  }, []);

  const captureStreamEvents = useCallback((events: CapturedStreamEvent[]) => {
    setLastTrace(projectStreamTrace(events));
    const bound = bindForensicTurn(events, provisionalUserInputRef.current);
    if (bound) {
      setForensicTurn(bound);
    }
  }, []);

  const value = useMemo(
    () => ({ lastTrace, forensicTurn, beginForensicTurn, captureStreamEvents }),
    [beginForensicTurn, captureStreamEvents, forensicTurn, lastTrace],
  );
  return <StreamTraceContext.Provider value={value}>{children}</StreamTraceContext.Provider>;
}

export function useStreamTrace(): StreamTraceContextValue {
  return useContext(StreamTraceContext);
}
