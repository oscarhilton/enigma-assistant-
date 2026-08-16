import type { DemoStatus } from "./types";

export type SimulationStatusProps = {
  status: DemoStatus | null;
};

export function SimulationStatus({ status }: SimulationStatusProps) {
  if (!status) {
    return (
      <section className="demo-panel" aria-label="Simulation status">
        <h2>Simulation status</h2>
        <p className="muted">Loading…</p>
      </section>
    );
  }

  return (
    <section className="demo-panel" aria-label="Simulation status">
      <h2>Simulation status</h2>
      <dl className="demo-status-grid">
        <div>
          <dt>Mode</dt>
          <dd>{status.mode}</dd>
        </div>
        <div>
          <dt>Scenario</dt>
          <dd>{status.scenario ?? "—"}</dd>
        </div>
        <div>
          <dt>Simulated time</dt>
          <dd data-testid="status-simulated-time">{status.simulated_time ?? "—"}</dd>
        </div>
        <div>
          <dt>Speed</dt>
          <dd>{status.paused ? "paused" : `${status.speed ?? "—"}×`}</dd>
        </div>
        <div>
          <dt>Ground truth in UI</dt>
          <dd>{status.ground_truth_visible ? "visible" : "hidden"}</dd>
        </div>
        {status.surfaced_count != null || status.suppressed_count != null ? (
          <div>
            <dt>Attention compression</dt>
            <dd data-testid="status-compression">
              {status.surfaced_count ?? "—"} surfaced ·{" "}
              {status.suppressed_count ?? "—"} suppressed
            </dd>
          </div>
        ) : null}
      </dl>
    </section>
  );
}
