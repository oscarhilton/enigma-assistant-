import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { switchWorld as switchWorldApi } from "./api";
import { WORLD_LABELS, type WorldId } from "./types";

type WorldContextValue = {
  world: WorldId;
  label: string;
  switchWorld: (world: WorldId) => Promise<void>;
};

const WorldContext = createContext<WorldContextValue | null>(null);

function defaultWorld(): WorldId {
  const mode = import.meta.env.VITE_ENIGMA_MODE as string | undefined;
  if (mode === "demo") {
    return "alex_lab";
  }
  return "my_enigma";
}

export function WorldProvider({
  children,
  initialWorld,
  persistToApi = false,
}: {
  children: ReactNode;
  initialWorld?: WorldId;
  persistToApi?: boolean;
}) {
  const [world, setWorld] = useState<WorldId>(initialWorld ?? defaultWorld());

  const switchWorld = useCallback(
    async (next: WorldId) => {
      if (next === world) {
        return;
      }
      if (persistToApi) {
        await switchWorldApi(next);
      }
      setWorld(next);
    },
    [persistToApi, world],
  );

  const value = useMemo(
    () => ({
      world,
      label: WORLD_LABELS[world],
      switchWorld,
    }),
    [switchWorld, world],
  );

  return <WorldContext.Provider value={value}>{children}</WorldContext.Provider>;
}

export function useWorld(): WorldContextValue {
  const value = useContext(WorldContext);
  if (!value) {
    throw new Error("useWorld requires WorldProvider");
  }
  return value;
}
