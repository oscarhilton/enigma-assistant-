import { useEffect, useRef, useState } from "react";
import { advanceDemoDay, advanceDemoStep, fetchDemoStatus, setDemoSpeed } from "./api";
import type { DemoStatus } from "./types";

const SPEEDS = [0, 1, 10, 100] as const;

/** Wall-clock ms between auto-play hour steps at 1× (higher speed ticks faster). */
const AUTO_PLAY_BASE_MS = 1000;

export type TimelineControlsProps = {
  fetchImpl?: typeof fetch;
  onStatusChange?: (status: DemoStatus) => void;
  initialStatus?: DemoStatus | null;
};

function autoPlayIntervalMs(speed: number): number {
  return Math.max(100, Math.round(AUTO_PLAY_BASE_MS / speed));
}

export function TimelineControls({
  fetchImpl = fetch,
  onStatusChange,
  initialStatus = null,
}: TimelineControlsProps) {
  const [status, setStatus] = useState<DemoStatus | null>(initialStatus);
  const [busy, setBusy] = useState(false);
  const onStatusChangeRef = useRef(onStatusChange);
  onStatusChangeRef.current = onStatusChange;

  function publish(next: DemoStatus) {
    setStatus(next);
    onStatusChangeRef.current?.(next);
  }

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const next = await fetchDemoStatus(fetchImpl);
      if (!cancelled) {
        publish(next);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount + fetchImpl only
  }, [fetchImpl]);

  const speed = status?.speed ?? 0;
  const paused = status?.paused ?? speed === 0;

  // Auto-play: speed > 0 advances one simulated hour per tick (1× ≈ 1s).
  useEffect(() => {
    if (paused || speed <= 0) {
      return;
    }
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const schedule = () => {
      timer = setTimeout(() => {
        void (async () => {
          if (cancelled) {
            return;
          }
          try {
            const next = await advanceDemoStep(fetchImpl);
            if (!cancelled) {
              publish(next);
            }
          } finally {
            if (!cancelled) {
              schedule();
            }
          }
        })();
      }, autoPlayIntervalMs(speed));
    };

    schedule();
    return () => {
      cancelled = true;
      if (timer !== undefined) {
        clearTimeout(timer);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only rebind when speed/pause change
  }, [fetchImpl, paused, speed]);

  async function apply(update: () => Promise<DemoStatus>) {
    setBusy(true);
    try {
      const next = await update();
      publish(next);
    } finally {
      setBusy(false);
    }
  }

  const simulatedTime = status?.simulated_time ?? "—";

  return (
    <section className="demo-panel" aria-label="Timeline controls">
      <h2>Timeline</h2>
      <p className="demo-time" data-testid="simulated-time">
        Simulated time: <time dateTime={status?.simulated_time ?? undefined}>{simulatedTime}</time>
      </p>
      <div className="cta-row">
        <button
          type="button"
          disabled={busy}
          onClick={() => void apply(() => advanceDemoStep(fetchImpl))}
        >
          Next event
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void apply(() => advanceDemoDay(fetchImpl))}
        >
          Next day
        </button>
      </div>
      <div className="demo-speed" role="group" aria-label="Simulation speed">
        <span className="muted">Speed</span>
        {SPEEDS.map((value) => (
          <button
            key={value}
            type="button"
            className={status?.speed === value ? "active" : undefined}
            disabled={busy}
            aria-pressed={status?.speed === value}
            onClick={() => void apply(() => setDemoSpeed(value, fetchImpl))}
          >
            {value === 0 ? "Pause" : `${value}×`}
          </button>
        ))}
      </div>
      <p className="muted demo-speed-hint">
        {paused || speed <= 0
          ? "Paused — use Next event / Next day, or pick a speed to auto-play."
          : `Auto-playing at ${speed}× (≈1 simulated hour every ${autoPlayIntervalMs(speed)}ms).`}
      </p>
    </section>
  );
}
