import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { DemoWhyPayload } from "./api";
import { fetchDemoWhy } from "./api";

export type WhyViewProps = {
  itemId?: string;
  fetchImpl?: typeof fetch;
};

export function WhyView({ itemId: itemIdProp, fetchImpl = fetch }: WhyViewProps) {
  const params = useParams();
  const itemId = itemIdProp ?? params.itemId ?? "att-atlas-review";
  const [payload, setPayload] = useState<DemoWhyPayload | null>(null);

  useEffect(() => {
    let cancelled = false;
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

  if (!payload) {
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

      <p className="muted">Reason codes: {payload.reason_codes.join(", ")}</p>
      <Link to="/demo/attention">Back to attention</Link>
    </section>
  );
}
