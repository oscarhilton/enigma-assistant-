import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { fetchWorlds, switchWorld as switchWorldApi } from "./api";
import { WORLD_LABELS, type WorldId } from "./types";

type WorldContextValue = {
  world: WorldId;
  label: string;
  switchWorld: (world: WorldId) => Promise<void>;
};

const WorldContext = createContext<WorldContextValue | null>(null);

function apiDefaultWorld(): WorldId {
  return "my_enigma";
}

function defaultWorld(): WorldId {
  const mode = import.meta.env.VITE_ENIGMA_MODE as string | undefined;
  if (mode === "demo") {
    return "alex_lab";
  }
  return "my_enigma";
}

function parseActiveWorld(value: string | undefined): WorldId | null {
  if (value === "alex_lab" || value === "my_enigma") {
    return value;
  }
  return null;
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
  const [world, setWorld] = useState<WorldId | null>(
    persistToApi ? null : (initialWorld ?? defaultWorld()),
  );

  useEffect(() => {
    if (!persistToApi) {
      return;
    }
    let cancelled = false;
    void fetchWorlds()
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setWorld(parseActiveWorld(payload.active) ?? initialWorld ?? apiDefaultWorld());
      })
      .catch(() => {
        if (!cancelled) {
          setWorld(initialWorld ?? apiDefaultWorld());
        }
      });
    return () => {
      cancelled = true;
    };
  }, [initialWorld, persistToApi]);

  const switchWorld = useCallback(
    async (next: WorldId) => {
      if (world == null || next === world) {
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
    () =>
      world == null
        ? null
        : {
            world,
            label: WORLD_LABELS[world],
            switchWorld,
          },
    [switchWorld, world],
  );

  if (world == null || value == null) {
    return (
      <div className="pilot-shell" data-testid="world-hydrating">
        Loading world…
      </div>
    );
  }

  return <WorldContext.Provider value={value}>{children}</WorldContext.Provider>;
}

export function useWorld(): WorldContextValue {
  const value = useContext(WorldContext);
  if (!value) {
    throw new Error("useWorld requires WorldProvider");
  }
  return value;
}
