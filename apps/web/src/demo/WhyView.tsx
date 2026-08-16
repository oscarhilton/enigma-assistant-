import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchDemoWhy } from "./api";
import type { DemoWhyPayload } from "./types";

export type WhyViewProps = {
  itemId?: string;
  fetchImpl?: typeof fetch;
};

function formatReasonCodes(codes: string[]): string {
  return codes.join(" · ");
}

/**
 * Structured provenance panel — Evidence → Inference → Decision → Why now?
 * Explains system evidence and policy, not model chain-of-thought.
 * Copy may use MODEL VIEW pseudonyms; the Attention dashboard uses PRIVATE UI names.
 */
export function WhyView({ itemId: itemIdProp, fetchImpl = fetch }: WhyViewProps) {
  const params = useParams();
  const itemId = itemIdProp ?? params.itemId ?? "att-atlas-review";
  const [payload, setPayload] = useState<DemoWhyPayload | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    setPayload(undefined);
    void (async () => {
      const next = await fetchDemoWhy(itemId, fetchImpl);
      if (!cancelled) {
        setPayload(next);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchImpl, itemId]);

  if (payload === undefined) {
    return (
      <section className="demo-panel" aria-label="Why view">
        <h2>Why?</h2>
        <p className="muted">Loading explanation…</p>
      </section>
    );
  }

  if (payload === null) {
    return (
      <section className="demo-panel" aria-label="Why view">
        <h2>Why?</h2>
        <p className="muted">No explanation available for {itemId}.</p>
        <Link to="/demo/attention">Back to attention</Link>
      </section>
    );
  }

  return (
    <section className="demo-panel" aria-label="Why view">
      <h2>{payload.headline}</h2>
      <p className="muted">Structured provenance — not model chain-of-thought.</p>

      <h3>Evidence</h3>
      <ul>
        {payload.evidence.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>

      <h3>Inference</h3>
      <ul>
        {payload.inference.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>

      <h3>Decision</h3>
      <ul>
        {payload.decision.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>

      <dl className="demo-why-metrics">
        <div>
          <dt>Priority</dt>
          <dd>
            {payload.priority}/5
          </dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{payload.confidence.toFixed(2)}</dd>
        </div>
      </dl>

      <h3>Why now?</h3>
      <ul>
        {payload.why_now.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>

      <p className="muted demo-reason-codes" aria-label="Reason codes">
        Reason codes: {formatReasonCodes(payload.reason_codes)}
      </p>
      <Link to="/demo/attention">Back to attention</Link>
    </section>
  );
}
