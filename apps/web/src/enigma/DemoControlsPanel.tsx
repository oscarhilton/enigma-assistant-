import { useEffect, useState } from "react";
import type { DemoStatus, EnigmaClient } from "./client";
import {
  copyTextToClipboard,
  formatLastTurnDump,
  formatSessionDump,
  tracesFromItems,
} from "./forensicDump";
import type { ConversationItem, DemoEvent } from "./types";

const SPEEDS = [0, 1, 10, 100] as const;

type Props = {
  client: EnigmaClient;
  checkpointId?: string | null;
  simulatedTime?: string | null;
  proactiveSilence?: boolean;
  showUnderBonnet?: boolean;
  onShowUnderBonnetChange?: (value: boolean) => void;
  items?: ConversationItem[];
};

function formatSimulatedLabel(iso: string | null | undefined): string | null {
  if (!iso) {
    return null;
  }
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return iso.slice(0, 16);
  }
  const month = parsed.toLocaleString("en-GB", { month: "short", timeZone: "UTC" });
  const day = parsed.getUTCDate();
  const hours = String(parsed.getUTCHours()).padStart(2, "0");
  const minutes = String(parsed.getUTCMinutes()).padStart(2, "0");
  return `${month} ${day} · ${hours}:${minutes}`;
}

function formatEventKind(event: DemoEvent): string {
  if (event.proactive_silence) {
    return "proactive silence";
  }
  return event.kind.replace(/_/g, " ");
}

export function DemoControlsPanel({
  client,
  checkpointId,
  simulatedTime,
  proactiveSilence = false,
  showUnderBonnet = false,
  onShowUnderBonnetChange,
  items = [],
}: Props) {
  const [open, setOpen] = useState(false);
  const [checkpoints, setCheckpoints] = useState<{ id: string; label: string }[]>([]);
  const [events, setEvents] = useState<DemoEvent[]>([]);
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const [jumping, setJumping] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<"session" | "turn" | null>(null);

  useEffect(() => {
    if (!copied) {
      return;
    }
    const id = window.setTimeout(() => setCopied(null), 1500);
    return () => window.clearTimeout(id);
  }, [copied]);

  useEffect(() => {
    if (!client.isDemo()) {
      return;
    }
    void client.listCheckpoints().then(setCheckpoints);
    void client.getDemoEvents().then(setEvents);
    void client.getDemoStatus().then(setStatus);
  }, [client, checkpointId, simulatedTime]);

  useEffect(() => {
    if (!client.isDemo()) {
      return;
    }
    const playing = (status?.speed ?? 0) > 0 && !status?.paused;
    if (!playing) {
      return;
    }
    const id = window.setInterval(() => {
      void client.getDemoStatus().then(setStatus);
    }, 1000);
    return () => window.clearInterval(id);
  }, [client, status?.paused, status?.speed]);

  useEffect(() => {
    if (!client.isDemo()) {
      return;
    }
    const unsub = client.subscribe((event) => {
      if (
        event.type === "attention_changed" ||
        event.type === "status_changed" ||
        event.type === "demo_event"
      ) {
        void client.getDemoEvents().then(setEvents);
        void client.getDemoStatus().then(setStatus);
      }
    });
    return unsub;
  }, [client]);

  if (!client.isDemo()) {
    return null;
  }

  const liveTime = status?.simulated_time ?? simulatedTime;
  const label =
    formatSimulatedLabel(liveTime) ??
    checkpoints.find((row) => row.id === checkpointId)?.label ??
    "Demo";

  async function applyTimeline(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
      const [nextEvents, nextStatus] = await Promise.all([
        client.getDemoEvents(),
        client.getDemoStatus(),
      ]);
      setEvents(nextEvents);
      setStatus(nextStatus);
    } finally {
      setBusy(false);
    }
  }

  async function handleJump(id: string) {
    setJumping(id);
    try {
      await client.jumpCheckpoint(id);
      const [nextEvents, nextCheckpoints] = await Promise.all([
        client.getDemoEvents(),
        client.listCheckpoints(),
      ]);
      setEvents(nextEvents);
      setCheckpoints(nextCheckpoints);
    } finally {
      setJumping(null);
    }
  }

  const traces = tracesFromItems(items);
  const canCopy = traces.length > 0;

  async function copyDump(kind: "session" | "turn") {
    const text = kind === "turn" ? formatLastTurnDump(traces) : formatSessionDump(traces);
    await copyTextToClipboard(text);
    setCopied(kind);
  }

  return (
    <div className="demo-controls">
      <div className="demo-controls-header">
        <button type="button" className="demo-controls-badge" onClick={() => setOpen((v) => !v)}>
          Demo · {label}
          {proactiveSilence ? " · silent" : ""}
        </button>
        <label className="demo-under-bonnet-toggle">
          <input
            type="checkbox"
            checked={showUnderBonnet}
            onChange={(event) => onShowUnderBonnetChange?.(event.target.checked)}
            data-testid="under-bonnet-toggle"
          />
          Show under the bonnet
        </label>
        <div className="demo-forensic-copy">
          <button
            type="button"
            className="demo-forensic-copy-button"
            data-testid="copy-debug"
            disabled={!canCopy}
            onClick={() => void copyDump("session")}
          >
            {copied === "session" ? "Copied" : "Copy debug"}
          </button>
          <button
            type="button"
            className="demo-forensic-copy-button"
            data-testid="copy-last-turn"
            disabled={!canCopy}
            onClick={() => void copyDump("turn")}
          >
            {copied === "turn" ? "Copied" : "Copy last turn"}
          </button>
        </div>
      </div>
      {open ? (
        <div className="demo-controls-panel">
          <p className="demo-controls-caption">Time machine — manipulates simulation, not fixtures.</p>
          <p className="demo-time" data-testid="demo-simulated-time">
            Simulated time:{" "}
            <time dateTime={status?.simulated_time ?? simulatedTime ?? undefined}>
              {status?.simulated_time ?? simulatedTime ?? "—"}
            </time>
          </p>
          <div className="cta-row demo-controls-timeline">
            <button
              type="button"
              disabled={busy || jumping !== null}
              onClick={() => void applyTimeline(() => client.advanceDemoStep())}
            >
              Next event
            </button>
            <button
              type="button"
              disabled={busy || jumping !== null}
              onClick={() => void applyTimeline(() => client.advanceDemoDay())}
            >
              Next day
            </button>
          </div>
          <div className="demo-speed" role="group" aria-label="Simulation speed">
            <span className="muted">Speed</span>
            {SPEEDS.map((speed) => (
              <button
                key={speed}
                type="button"
                className={status?.speed === speed ? "active" : undefined}
                disabled={busy || jumping !== null}
                onClick={() => void applyTimeline(() => client.setDemoSpeed(speed))}
              >
                {speed === 0 ? "Pause" : `${speed}×`}
              </button>
            ))}
          </div>
          {proactiveSilence ? (
            <p className="demo-controls-silence" data-testid="demo-silence-hint">
              Proactive silence — nothing added to the conversation.
            </p>
          ) : null}
          <div className="demo-controls-checkpoints">
            {checkpoints.map((checkpoint) => (
              <button
                key={checkpoint.id}
                type="button"
                aria-pressed={checkpoint.id === checkpointId}
                disabled={jumping !== null}
                onClick={() => void handleJump(checkpoint.id)}
              >
                {jumping === checkpoint.id ? "Jumping…" : checkpoint.label}
              </button>
            ))}
          </div>
          <ul className="demo-event-log">
            {events.length === 0 ? (
              <li className="demo-event-log-empty">No demo events yet.</li>
            ) : (
              events.slice(-5).map((event, index) => (
                <li key={`${event.at}-${index}`}>
                  {event.at.slice(11, 16)} — {formatEventKind(event)}
                </li>
              ))
            )}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
