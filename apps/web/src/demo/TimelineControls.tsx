import { useEffect, useState } from "react";
import {
  advanceDemoDay,
  advanceDemoStep,
  fetchDemoStatus,
  resetDemo,
  setDemoSpeed,
} from "./api";
import type { DemoStatus } from "./types";

const SPEEDS = [0, 1, 10, 100] as const;

const RESET_CONFIRM =
  "Reset demo? This wipes Demo storage for the active scenario and reseeds from the scenario epoch. Private and Shadow data are not touched.";

export type TimelineControlsProps = {
  fetchImpl?: typeof fetch;
  onStatusChange?: (status: DemoStatus) => void;
  initialStatus?: DemoStatus | null;
  confirmImpl?: (message: string) => boolean;
};

export function TimelineControls({
  fetchImpl = fetch,
  onStatusChange,
  initialStatus = null,
  confirmImpl = window.confirm.bind(window),
}: TimelineControlsProps) {
  const [status, setStatus] = useState<DemoStatus | null>(initialStatus);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const next = await fetchDemoStatus(fetchImpl);
      if (!cancelled) {
        setStatus(next);
        onStatusChange?.(next);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchImpl, onStatusChange]);

  async function apply(update: () => Promise<DemoStatus>) {
    setBusy(true);
    try {
      const next = await update();
      setStatus(next);
      onStatusChange?.(next);
    } finally {
      setBusy(false);
    }
  }

  function onResetClick() {
    if (!confirmImpl(RESET_CONFIRM)) {
      return;
    }
    void apply(() => resetDemo(fetchImpl));
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
        <button type="button" className="demo-reset" disabled={busy} onClick={onResetClick}>
          Reset demo
        </button>
      </div>
      <div className="demo-speed" role="group" aria-label="Simulation speed">
        <span className="muted">Speed</span>
        {SPEEDS.map((speed) => (
          <button
            key={speed}
            type="button"
            className={status?.speed === speed ? "active" : undefined}
            disabled={busy}
            onClick={() => void apply(() => setDemoSpeed(speed, fetchImpl))}
          >
            {speed === 0 ? "Pause" : `${speed}×`}
          </button>
        ))}
      </div>
    </section>
  );
}
