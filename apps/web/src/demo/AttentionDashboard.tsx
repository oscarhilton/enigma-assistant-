import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDemoAttention, postDemoAttentionAction } from "./api";
import {
  canWaitLabel,
  cardReason,
  compactBadges,
  mattersNowHeadline,
} from "./attentionCardCopy";
import type { DemoAttentionItem, DemoAttentionPayload } from "./types";

export type AttentionDashboardProps = {
  fetchImpl?: typeof fetch;
  /** Secondary line under the product promise; omit in Private Mode reuse. */
  scenarioLabel?: string;
};

function sortByRank(items: DemoAttentionItem[]): DemoAttentionItem[] {
  return [...items].sort((a, b) => b.attention_rank - a.attention_rank);
}

/**
 * Private UI attention surface — real synthetic names (Maya, Atlas).
 * Reason codes, PERSON_*, and evidence dumps live in Why / privacy views.
 */
export function AttentionDashboard({
  fetchImpl = fetch,
  scenarioLabel = "Alex Morgan",
}: AttentionDashboardProps) {
  const [payload, setPayload] = useState<DemoAttentionPayload | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [showCanWait, setShowCanWait] = useState(false);

  const load = useCallback(
    async (isCancelled?: () => boolean) => {
      const next = await fetchDemoAttention(fetchImpl);
      if (isCancelled?.()) {
        return;
      }
      setPayload({
        ...next,
        items: sortByRank(next.items),
      });
    },
    [fetchImpl],
  );

  useEffect(() => {
    let cancelled = false;
    void load(() => cancelled);
    return () => {
      cancelled = true;
    };
  }, [load]);

  async function onAction(itemId: string, action: "done" | "snooze") {
    setBusyId(itemId);
    try {
      const result = await postDemoAttentionAction(itemId, action, fetchImpl);
      setPayload((prev) => {
        const surfaced = result.surfaced_count ?? result.items.length;
        const suppressed = result.suppressed_count ?? prev?.suppressed_count;
        return {
          items: sortByRank(result.items),
          signals_considered:
            result.signals_considered ??
            (suppressed != null ? surfaced + suppressed : prev?.signals_considered),
          surfaced_count: surfaced,
          suppressed_count: suppressed,
          simulated_time: prev?.simulated_time,
        };
      });
    } finally {
      setBusyId(null);
    }
  }

  const items = payload?.items ?? [];
  const surfaced = payload?.surfaced_count ?? items.length;
  const suppressed = payload?.suppressed_count;
  const headlineCount = payload ? surfaced : items.length;

  return (
    <section className="demo-panel" aria-label="Attention dashboard">
      <h2 data-testid="attention-headline">{mattersNowHeadline(headlineCount)}</h2>
      {scenarioLabel ? (
        <p className="muted demo-attention-scenario">Fictional scenario · {scenarioLabel}</p>
      ) : null}

      {suppressed != null && suppressed > 0 ? (
        <div className="demo-attention-can-wait">
          <button
            type="button"
            className="demo-link-button"
            data-testid="attention-can-wait"
            aria-expanded={showCanWait}
            onClick={() => setShowCanWait((open) => !open)}
          >
            {showCanWait ? "Hide what can wait" : canWaitLabel(suppressed)}
          </button>
          {showCanWait ? (
            <p className="muted demo-attention-can-wait-note">
              Enigma is holding {suppressed} lower-priority signal
              {suppressed === 1 ? "" : "s"} out of view so you can focus on what
              matters now.
            </p>
          ) : null}
        </div>
      ) : null}

      <ul className="demo-list">
        {items.map((item) => {
          const badges = compactBadges(item);
          const reason = cardReason(item);
          return (
            <li key={item.id} className="demo-attention-card">
              <div className="demo-list-main">
                <strong className="demo-attention-what">{item.title}</strong>
                {badges.length > 0 ? (
                  <p
                    className="demo-attention-badges"
                    data-testid={`attention-badges-${item.id}`}
                  >
                    {badges.join(" · ")}
                  </p>
                ) : null}
                {reason ? (
                  <p className="demo-attention-reason">{reason}</p>
                ) : null}
              </div>
              <div className="demo-attention-actions">
                <Link to={`/demo/why/${item.id}`}>Why?</Link>
                <button
                  type="button"
                  disabled={busyId === item.id}
                  onClick={() => void onAction(item.id, "done")}
                >
                  Done
                </button>
                <button
                  type="button"
                  disabled={busyId === item.id}
                  onClick={() => void onAction(item.id, "snooze")}
                >
                  Snooze
                </button>
              </div>
            </li>
          );
        })}
      </ul>

      {items.length === 0 && payload ? (
        <p className="muted">
          No open attention items.{" "}
          <button type="button" className="demo-link-button" onClick={() => void load()}>
            Refresh
          </button>
        </p>
      ) : null}
    </section>
  );
}
