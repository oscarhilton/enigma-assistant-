import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDemoAttention } from "./api";
import type { DemoAttentionItem } from "./api";

export type AttentionDashboardProps = {
  fetchImpl?: typeof fetch;
};

export function AttentionDashboard({ fetchImpl = fetch }: AttentionDashboardProps) {
  const [items, setItems] = useState<DemoAttentionItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const next = await fetchDemoAttention(fetchImpl);
      if (!cancelled) {
        setItems(next);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchImpl]);

  return (
    <section className="demo-panel" aria-label="Attention dashboard">
      <h2>Attention</h2>
      <p className="muted">What actually matters in the fictional scenario right now.</p>
      <ul className="demo-list">
        {items.map((item) => (
          <li key={item.id}>
            <div className="demo-list-main">
              <strong>{item.title}</strong>
              <span className="muted">
                {item.kind} · score {item.score.toFixed(2)}
              </span>
              <p>{item.body}</p>
            </div>
            <Link to={`/demo/why/${item.id}`}>Why?</Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
