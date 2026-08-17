import { useEffect, useMemo, useState } from "react";
import type { EnigmaClient } from "../client";
import {
  BRAIN_REGION_LABELS,
  formatBrainEventLabel,
  RETENTION_STAGE_METRICS,
  type BrainEvent,
  type BrainRegion,
  type RetentionStage,
} from "./events";
import {
  mergeBrainEvents,
  projectDemoEvents,
  projectEgressDisclosure,
  projectEnigmaEvent,
} from "./mapEvents";

type Props = {
  client: EnigmaClient;
};

const REGION_LAYOUT_ORDER: BrainRegion[] = ["input", "upper", "centre", "right", "membrane", "shadow"];

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function RegionLegend({ privacyMode }: { privacyMode: boolean }) {
  return (
    <div className="cortex-regions" data-testid="cortex-region-legend">
      {REGION_LAYOUT_ORDER.map((region) => {
        const meta = BRAIN_REGION_LABELS[region];
        const collapsed = privacyMode && (region === "centre" || region === "input");
        return (
          <div
            key={region}
            className={`cortex-region cortex-region-${meta.layout}${collapsed ? " cortex-region-collapsed" : ""}`}
            data-region={region}
          >
            <strong>{meta.title}</strong>
            <span>{meta.description}</span>
          </div>
        );
      })}
    </div>
  );
}

function RetentionSlider({
  stage,
  onStageChange,
}: {
  stage: RetentionStage;
  onStageChange: (stage: RetentionStage) => void;
}) {
  const metrics =
    RETENTION_STAGE_METRICS.find((row) => row.stage === stage) ?? RETENTION_STAGE_METRICS[2]!;

  return (
    <div className="cortex-retention" data-testid="cortex-retention-slider">
      <header>
        <h3>Retention curve (SEC-07 stub)</h3>
        <p>Utility vs reconstructability across SOURCE → ACTIVE → SHADOW → FORGOTTEN.</p>
      </header>
      <input
        type="range"
        min={0}
        max={RETENTION_STAGE_METRICS.length - 1}
        step={1}
        value={RETENTION_STAGE_METRICS.findIndex((row) => row.stage === stage)}
        aria-label="Retention stage"
        onChange={(event) => {
          const next = RETENTION_STAGE_METRICS[Number(event.target.value)];
          if (next) {
            onStageChange(next.stage);
          }
        }}
      />
      <div className="cortex-retention-labels">
        {RETENTION_STAGE_METRICS.map((row) => (
          <span key={row.stage} className={row.stage === stage ? "active" : undefined}>
            {row.stage.toUpperCase()}
          </span>
        ))}
      </div>
      <dl className="cortex-retention-metrics">
        <div>
          <dt>Utility</dt>
          <dd>{metrics.utility_pct}%</dd>
        </div>
        <div>
          <dt>Reconstructability</dt>
          <dd>{metrics.reconstructability_pct}%</dd>
        </div>
      </dl>
    </div>
  );
}

function BrainEventRow({ event }: { event: BrainEvent }) {
  const region = BRAIN_REGION_LABELS[event.region];
  return (
    <li className="cortex-event-row" data-testid={`cortex-event-${event.type}`}>
      <span className="cortex-event-time">{formatTimestamp(event.at)}</span>
      <span className="cortex-event-region">{region.title}</span>
      <span className="cortex-event-label">{formatBrainEventLabel(event)}</span>
    </li>
  );
}

export function CortexPanel({ client }: Props) {
  const [open, setOpen] = useState(false);
  const [privacyMode, setPrivacyMode] = useState(false);
  const [retentionStage, setRetentionStage] = useState<RetentionStage>("shadow");
  const [events, setEvents] = useState<BrainEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const tasks: Promise<BrainEvent[]>[] = [];
        if (client.isDemo()) {
          tasks.push(client.getDemoEvents().then(projectDemoEvents));
        }
        tasks.push(
          client.getRecentDisclosures().then((rows) => rows.map(projectEgressDisclosure)),
        );
        const groups = await Promise.all(tasks);
        if (!cancelled) {
          setEvents(mergeBrainEvents(...groups));
        }
      } catch (cause: unknown) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Failed to load cortex events");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    const unsub = client.subscribe((event) => {
      const projected = projectEnigmaEvent(event);
      if (projected.length === 0) {
        return;
      }
      setEvents((current) => mergeBrainEvents(current, projected));
    });
    return () => {
      cancelled = true;
      unsub();
    };
  }, [client, open]);

  const visibleEvents = useMemo(() => {
    if (!privacyMode) {
      return events;
    }
    return events.filter((event) => event.region === "membrane" || event.region === "shadow");
  }, [events, privacyMode]);

  return (
    <div className="cortex-panel-root" data-testid="cortex-panel-root">
      <button
        type="button"
        className="cortex-panel-toggle"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        Cortex
      </button>
      {open ? (
        <section className="cortex-panel" aria-label="Cortex brain visualizer">
          <header className="cortex-panel-header">
            <h2>Cortex</h2>
            <p>Read-only observability — state transitions and privacy boundary, not LLM chain-of-thought.</p>
          </header>

          <RegionLegend privacyMode={privacyMode} />

          <div className="cortex-scene-placeholder" data-testid="cortex-scene-placeholder">
            <p>Three.js network scene — future work (react-three-fiber).</p>
            <button
              type="button"
              className={`cortex-membrane-toggle${privacyMode ? " active" : ""}`}
              aria-pressed={privacyMode}
              onClick={() => setPrivacyMode((value) => !value)}
            >
              {privacyMode ? "What left the brain (on)" : "What left the brain"}
            </button>
            {privacyMode ? (
              <p className="cortex-privacy-caption">
                Privacy mode — centre/input collapsed to shadow abstraction. Membrane egress events highlighted.
              </p>
            ) : null}
          </div>

          <RetentionSlider stage={retentionStage} onStageChange={setRetentionStage} />

          <section className="cortex-event-log" aria-label="Brain event log">
            <h3>Event log</h3>
            {loading ? <p className="cortex-caption">Loading events…</p> : null}
            {error ? <p className="cortex-error">{error}</p> : null}
            {!loading && !error && visibleEvents.length === 0 ? (
              <p className="cortex-caption">No brain events yet — interact with Demo or trigger egress.</p>
            ) : null}
            {!loading && visibleEvents.length > 0 ? (
              <ol className="cortex-event-list">
                {visibleEvents
                  .slice()
                  .reverse()
                  .slice(0, 30)
                  .map((event) => (
                    <BrainEventRow key={event.id} event={event} />
                  ))}
              </ol>
            ) : null}
          </section>
        </section>
      ) : null}
    </div>
  );
}
