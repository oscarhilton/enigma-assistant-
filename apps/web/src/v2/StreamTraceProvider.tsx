import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { projectStreamTrace, type CapturedStreamEvent, type StreamingTraceProjection } from "./streamTrace";

type StreamTraceContextValue = {
  lastTrace: StreamingTraceProjection | null;
  captureStreamEvents: (events: CapturedStreamEvent[]) => void;
};

const StreamTraceContext = createContext<StreamTraceContextValue>({
  lastTrace: null,
  captureStreamEvents: () => undefined,
});

export function StreamTraceProvider({ children }: { children: ReactNode }) {
  const [lastTrace, setLastTrace] = useState<StreamingTraceProjection | null>(null);
  const captureStreamEvents = useCallback((events: CapturedStreamEvent[]) => {
    setLastTrace(projectStreamTrace(events));
  }, []);
  const value = useMemo(
    () => ({ lastTrace, captureStreamEvents }),
    [captureStreamEvents, lastTrace],
  );
  return <StreamTraceContext.Provider value={value}>{children}</StreamTraceContext.Provider>;
}

export function useStreamTrace(): StreamTraceContextValue {
  return useContext(StreamTraceContext);
}
