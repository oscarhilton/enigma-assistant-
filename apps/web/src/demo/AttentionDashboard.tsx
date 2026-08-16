import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDemoAttention, fetchDemoSuppressed, postDemoAttentionAction } from "./api";
import {
  canWaitLabel,
  cardReason,
  compactBadges,
  holdingSignalsNote,
  lastEvaluatedLabel,
  mattersNowHeadline,
  resolveCanWaitGroups,
} from "./attentionCardCopy";
import {
  cycleNextIndex,
  nextActionLine,
  nextSectionLabel,
  resolveNextActionCandidates,
} from "./nextActionCopy";
import type {
  CanWaitCategoryId,
  CanWaitGroup,
  DemoAttentionItem,
  DemoAttentionPayload,
  DemoNextAction,
  DemoSuppressedItem,
} from "./types";

export type AttentionDashboardProps = {
  fetchImpl?: typeof fetch;
  /** Secondary line under the product promise; omit in Private Mode reuse. */
  scenarioLabel?: string;
  /** Test hook: fixed "now" for last-evaluated copy. */
  nowMs?: number;
};

function sortByRank(items: DemoAttentionItem[]): DemoAttentionItem[] {
  return [...items].sort((a, b) => b.attention_rank - a.attention_rank);
}

/**
 * Private UI attention surface — real synthetic names (Maya, Atlas).
 * Three levels: NEEDS YOU (Attention) · WORTH DOING (Next) · CAN WAIT.
 * Shape is frozen for Demo (see docs/architecture/attention-surface.md).
 */
export function AttentionDashboard({
  fetchImpl = fetch,
  scenarioLabel = "Alex Morgan",
  nowMs,
}: AttentionDashboardProps) {
  const [payload, setPayload] = useState<DemoAttentionPayload | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [showCanWait, setShowCanWait] = useState(false);
  const [expandedGroup, setExpandedGroup] = useState<CanWaitCategoryId | null>(
    null,
  );
  const [suppressedItems, setSuppressedItems] = useState<DemoSuppressedItem[]>(
    [],
  );
  const [evaluatedAtMs, setEvaluatedAtMs] = useState<number | null>(null);
  const [clockMs, setClockMs] = useState(() => nowMs ?? Date.now());
  const [nextIndex, setNextIndex] = useState(0);
  const [nextAccepted, setNextAccepted] = useState(false);

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
      setNextIndex(0);
      setNextAccepted(false);
      const fromApi = next.evaluated_at
        ? Date.parse(next.evaluated_at)
        : Number.NaN;
      setEvaluatedAtMs(Number.isFinite(fromApi) ? fromApi : Date.now());
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

  useEffect(() => {
    if (nowMs != null) {
      setClockMs(nowMs);
      return;
    }
    const id = window.setInterval(() => {
      setClockMs(Date.now());
    }, 15_000);
    return () => {
      window.clearInterval(id);
    };
  }, [nowMs]);

  useEffect(() => {
    if (!showCanWait) {
      return;
    }
    let cancelled = false;
    void (async () => {
      const suppressed = await fetchDemoSuppressed(null, fetchImpl);
      if (!cancelled) {
        setSuppressedItems(suppressed.items);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [showCanWait, fetchImpl]);

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
          can_wait_groups: prev?.can_wait_groups,
          next_actions: prev?.next_actions,
          evaluated_at: prev?.evaluated_at,
          simulated_time: prev?.simulated_time,
        };
      });
      setNextIndex(0);
      setNextAccepted(false);
      setEvaluatedAtMs(Date.now());
    } finally {
      setBusyId(null);
    }
  }

  const items = payload?.items ?? [];
  const surfaced = payload?.surfaced_count ?? items.length;
  const suppressed = payload?.suppressed_count;
  const headlineCount = payload ? surfaced : items.length;
  const attentionEmpty = headlineCount <= 0;

  const nextCandidates: DemoNextAction[] = useMemo(
    () => resolveNextActionCandidates(items, payload?.next_actions),
    [items, payload?.next_actions],
  );

  const activeNext =
    nextCandidates.length > 0
      ? nextCandidates[Math.min(nextIndex, nextCandidates.length - 1)]!
      : null;

  const canWaitGroups: CanWaitGroup[] = useMemo(() => {
    if (suppressed == null || suppressed <= 0) {
      return [];
    }
    return resolveCanWaitGroups(
      suppressed,
      payload?.can_wait_groups,
      suppressedItems,
    );
  }, [suppressed, payload?.can_wait_groups, suppressedItems]);

  const evaluatedLabel =
    evaluatedAtMs != null
      ? lastEvaluatedLabel(evaluatedAtMs, clockMs)
      : null;

  return (
    <section className="demo-panel" aria-label="Attention dashboard">
      <h2 data-testid="attention-headline">{mattersNowHeadline(headlineCount)}</h2>
      {scenarioLabel ? (
        <p className="muted demo-attention-scenario">
          Fictional scenario · {scenarioLabel}
        </p>
      ) : null}

      {items.length > 0 ? (
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
      ) : null}

      {activeNext ? (
        <div
          className="demo-next-action"
          data-testid="attention-next-action"
          data-optional="true"
          data-category={activeNext.category}
        >
          <p className="demo-next-action-label" data-testid="attention-next-label">
            {nextSectionLabel(attentionEmpty)}
          </p>
          <p className="demo-next-action-line" data-testid="attention-next-line">
            {nextActionLine(activeNext)}
          </p>
          <p className="muted demo-next-action-reason">{activeNext.reason}</p>
          <div className="demo-next-action-actions">
            <button
              type="button"
              data-testid="attention-next-accept"
              disabled={nextAccepted}
              onClick={() => setNextAccepted(true)}
            >
              {attentionEmpty ? "I'll do that" : "Let's do it"}
            </button>
            <button
              type="button"
              className="demo-link-button"
              data-testid="attention-next-something-else"
              onClick={() => {
                setNextAccepted(false);
                setNextIndex((i) => cycleNextIndex(i, nextCandidates.length));
              }}
            >
              Something else
            </button>
          </div>
          {nextAccepted ? (
            <p className="muted demo-next-action-ack" data-testid="attention-next-ack">
              Noted — Demo only; Shadow will not intervene.
            </p>
          ) : null}
        </div>
      ) : null}

      {suppressed != null && suppressed > 0 ? (
        <div className="demo-attention-can-wait" data-testid="attention-can-wait-block">
          {!attentionEmpty ? (
            <p
              className="muted demo-attention-can-wait-note"
              data-testid="attention-holding-note"
            >
              {holdingSignalsNote(suppressed)}
            </p>
          ) : null}
          <button
            type="button"
            className="demo-link-button"
            data-testid="attention-can-wait"
            aria-expanded={showCanWait}
            onClick={() => {
              setShowCanWait((open) => {
                const next = !open;
                if (!next) {
                  setExpandedGroup(null);
                }
                return next;
              });
            }}
          >
            {showCanWait ? "Hide what can wait" : canWaitLabel(suppressed)}
          </button>
          {showCanWait ? (
            <>
              {attentionEmpty ? (
                <p
                  className="muted demo-attention-can-wait-note"
                  data-testid="attention-holding-note"
                >
                  {holdingSignalsNote(suppressed)}
                </p>
              ) : null}
              <ul
                className="demo-attention-can-wait-groups"
                data-testid="attention-can-wait-groups"
              >
                {canWaitGroups.map((group) => {
                  const open = expandedGroup === group.id;
                  const samples = suppressedItems.filter(
                    (item) =>
                      (item.can_wait_category ?? null) === group.id ||
                      (!item.can_wait_category &&
                        ((group.id === "informational" &&
                          item.suppression_reason === "newsletter") ||
                          (group.id === "automated_noise" &&
                            (item.suppression_reason === "spam" ||
                              item.suppression_reason === "background")))),
                  );
                  return (
                    <li key={group.id}>
                      <button
                        type="button"
                        className="demo-link-button demo-attention-can-wait-group-toggle"
                        data-testid={`can-wait-group-${group.id}`}
                        aria-expanded={open}
                        onClick={() =>
                          setExpandedGroup((cur) =>
                            cur === group.id ? null : group.id,
                          )
                        }
                      >
                        {group.label}
                        <span className="demo-attention-can-wait-count">
                          · {group.count}
                        </span>
                      </button>
                      {open && samples.length > 0 ? (
                        <ul className="demo-attention-can-wait-group-detail muted">
                          {samples.slice(0, 3).map((sample) => (
                            <li key={sample.id}>{sample.message}</li>
                          ))}
                        </ul>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </>
          ) : null}
        </div>
      ) : null}

      {evaluatedLabel ? (
        <p className="muted demo-attention-evaluated" data-testid="attention-last-evaluated">
          {evaluatedLabel}
        </p>
      ) : null}
    </section>
  );
}
