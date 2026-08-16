import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchDemoWhy } from "./api";
import type { DemoWhyPayload } from "./types";

export type WhyViewProps = {
  itemId?: string;
  fetchImpl?: typeof fetch;
};

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

      <p className="muted">Reason codes: {payload.reason_codes.join(", ")}</p>
      <Link to="/demo/attention">Back to attention</Link>
    </section>
  );
}
