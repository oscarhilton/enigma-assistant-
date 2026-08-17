import { useEffect, useState } from "react";
import type { EnigmaClient } from "./client";
import {
  copyTextToClipboard,
  formatLastTurnDump,
  formatSessionDump,
  tracesFromItems,
} from "./forensicDump";
import type { ConversationItem, DemoEvent } from "./types";

type Props = {
  client: EnigmaClient;
  checkpointId?: string | null;
  simulatedTime?: string | null;
  proactiveSilence?: boolean;
  showUnderBonnet?: boolean;
  onShowUnderBonnetChange?: (value: boolean) => void;
  items?: ConversationItem[];
};

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
  const [jumping, setJumping] = useState<string | null>(null);
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
  }, [client, checkpointId]);

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
      }
    });
    return unsub;
  }, [client]);

  if (!client.isDemo()) {
    return null;
  }

  const label =
    checkpoints.find((row) => row.id === checkpointId)?.label ??
    simulatedTime?.slice(0, 16) ??
    "Demo";

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
