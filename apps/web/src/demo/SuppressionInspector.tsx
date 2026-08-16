import { useCallback, useEffect, useState } from "react";
import { fetchDemoSuppressed } from "./api";
import type { DemoSuppressedPayload, DemoSuppressionReason } from "./types";

export type SuppressionInspectorProps = {
  fetchImpl?: typeof fetch;
};

function reasonLabel(reason: string): string {
  return reason.replaceAll("_", " ");
}

/**
 * Developer-only suppression inspector (`/demo/suppressed`).
 * Shows why-not-surfaced samples; never ScenarioSignalClass / ground truth.
 */
export function SuppressionInspector({ fetchImpl = fetch }: SuppressionInspectorProps) {
  const [filter, setFilter] = useState<DemoSuppressionReason | null>(null);
  const [payload, setPayload] = useState<DemoSuppressedPayload | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = useCallback(
    async (reason: DemoSuppressionReason | null, isCancelled?: () => boolean) => {
      const next = await fetchDemoSuppressed(reason, fetchImpl);
      if (isCancelled?.()) {
        return;
      }
      setPayload(next);
    },
    [fetchImpl],
  );

  useEffect(() => {
    let cancelled = false;
    void load(filter, () => cancelled);
    return () => {
      cancelled = true;
    };
  }, [filter, load]);

  const filters = payload?.filters ?? [];
  const items = payload?.items ?? [];

  return (
    <section className="demo-panel" aria-label="Suppression inspector">
      <h2>Suppression inspector</h2>
      <p className="muted">
        Developer-only · why signals were not surfaced. Not part of product demo chrome.
      </p>

      {payload ? (
        <p className="demo-attention-footer" data-testid="suppression-compression">
          {payload.signals_considered} signals considered · {payload.surfaced_count}{" "}
          surfaced · {payload.suppressed_count} suppressed
        </p>
      ) : (
        <p className="muted">Loading…</p>
      )}

      <div className="demo-suppress-filters" role="group" aria-label="Suppression filters">
        <button
          type="button"
          aria-pressed={filter == null}
          onClick={() => setFilter(null)}
        >
          all
        </button>
        {filters.map((reason) => (
          <button
            key={reason}
            type="button"
            aria-pressed={filter === reason}
            onClick={() => setFilter(reason)}
          >
            {reasonLabel(reason)}
          </button>
        ))}
      </div>

      <ul className="demo-list">
        {items.map((item) => {
          const open = expandedId === item.id;
          return (
            <li key={item.id} className="demo-attention-card">
              <div className="demo-list-main">
                <strong>{item.message}</strong>
                <dl className="demo-attention-meta">
                  <div>
                    <dt>Reason</dt>
                    <dd>{reasonLabel(item.suppression_reason)}</dd>
                  </div>
                  <div>
                    <dt>Classification</dt>
                    <dd>{item.classification}</dd>
                  </div>
                  <div>
                    <dt>Decision</dt>
                    <dd>{item.decision}</dd>
                  </div>
                </dl>
                <button
                  type="button"
                  className="demo-link-button"
                  aria-expanded={open}
                  onClick={() => setExpandedId(open ? null : item.id)}
                >
                  {open ? "Hide why-not" : "Why was this NOT surfaced?"}
                </button>
                {open ? (
                  <dl className="demo-why-not" data-testid={`why-not-${item.id}`}>
                    <div>
                      <dt>Open obligation</dt>
                      <dd>{item.open_obligation}</dd>
                    </div>
                    <div>
                      <dt>Relationship relevance</dt>
                      <dd>{item.relationship_relevance}</dd>
                    </div>
                    <div>
                      <dt>Deadline</dt>
                      <dd>{item.deadline}</dd>
                    </div>
                    <div>
                      <dt>Why not</dt>
                      <dd>
                        <ul>
                          {item.why_not.map((line) => (
                            <li key={line}>{line}</li>
                          ))}
                        </ul>
                      </dd>
                    </div>
                  </dl>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>

      {payload && items.length === 0 ? (
        <p className="muted">No sample rows for this filter.</p>
      ) : null}
    </section>
  );
}
