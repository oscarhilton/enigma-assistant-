import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDemoAttention, postDemoAttentionAction } from "./api";
import type { DemoAttentionItem, DemoAttentionPayload } from "./types";

export type AttentionDashboardProps = {
  fetchImpl?: typeof fetch;
  /** Secondary line under the product promise; omit in Private Mode reuse. */
  scenarioLabel?: string;
};

function kindLabel(kind: string): string {
  return kind.replaceAll("_", "-").toUpperCase();
}

function sortByRank(items: DemoAttentionItem[]): DemoAttentionItem[] {
  return [...items].sort((a, b) => b.attention_rank - a.attention_rank);
}

/**
 * Private UI attention surface — real synthetic names (Maya, Atlas).
 * Reason codes and PERSON_* live in Why / privacy views, not here.
 */
export function AttentionDashboard({
  fetchImpl = fetch,
  scenarioLabel = "Alex Morgan",
}: AttentionDashboardProps) {
  const [payload, setPayload] = useState<DemoAttentionPayload | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

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
      setPayload((prev) => ({
        items: sortByRank(result.items),
        surfaced_count: result.surfaced_count ?? result.items.length,
        suppressed_count: result.suppressed_count ?? prev?.suppressed_count,
        simulated_time: prev?.simulated_time,
      }));
    } finally {
      setBusyId(null);
    }
  }

  const items = payload?.items ?? [];
  const surfaced = payload?.surfaced_count ?? items.length;
  const suppressed = payload?.suppressed_count;

  return (
    <section className="demo-panel" aria-label="Attention dashboard">
      <h2>Attention</h2>
      <p className="demo-attention-promise">What actually matters right now.</p>
      {scenarioLabel ? (
        <p className="muted demo-attention-scenario">Fictional scenario · {scenarioLabel}</p>
      ) : null}

      <ul className="demo-list">
        {items.map((item) => (
          <li key={item.id} className="demo-attention-card">
            <div className="demo-list-main">
              <strong className="demo-attention-what">{item.title}</strong>
              <dl className="demo-attention-meta">
                {item.when ? (
                  <div>
                    <dt>When</dt>
                    <dd>{item.when}</dd>
                  </div>
                ) : null}
                {item.why_now_glance ? (
                  <div>
                    <dt>Why now</dt>
                    <dd>{item.why_now_glance}</dd>
                  </div>
                ) : null}
                <div>
                  <dt>Kind</dt>
                  <dd>{kindLabel(item.kind)}</dd>
                </div>
                <div>
                  <dt>Priority</dt>
                  <dd>{item.priority}/5</dd>
                </div>
                <div>
                  <dt>Confidence</dt>
                  <dd>{item.confidence.toFixed(2)}</dd>
                </div>
              </dl>
              <p>{item.body}</p>
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
        ))}
      </ul>

      {suppressed != null ? (
        <p className="muted demo-attention-footer">
          {surfaced} items surfaced · {suppressed} signals suppressed
        </p>
      ) : null}

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
