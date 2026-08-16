import { useEffect, useMemo, useState } from "react";
import { fetchDemoMemory } from "./api";
import type { DemoMemoryItem } from "./api";

export type MemoryBrowserProps = {
  fetchImpl?: typeof fetch;
};

export function MemoryBrowser({ fetchImpl = fetch }: MemoryBrowserProps) {
  const [items, setItems] = useState<DemoMemoryItem[]>([]);
  const [category, setCategory] = useState<string>("All");

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const next = await fetchDemoMemory(fetchImpl);
      if (!cancelled) {
        setItems(next);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchImpl]);

  const categories = useMemo(
    () => ["All", ...Array.from(new Set(items.map((item) => item.category))).sort()],
    [items],
  );

  const visible =
    category === "All" ? items : items.filter((item) => item.category === category);

  return (
    <section className="demo-panel" aria-label="Memory browser">
      <h2>Memory</h2>
      <p className="muted">
        Learned statements from the demo pipeline. Ground truth is never shown here.
      </p>
      <div className="demo-speed" role="tablist" aria-label="Memory categories">
        {categories.map((name) => (
          <button
            key={name}
            type="button"
            role="tab"
            aria-selected={category === name}
            className={category === name ? "active" : undefined}
            onClick={() => setCategory(name)}
          >
            {name}
          </button>
        ))}
      </div>
      <ul className="demo-list">
        {visible.map((item) => (
          <li key={item.id}>
            <div className="demo-list-main">
              <strong>{item.statement}</strong>
              <span className="muted">
                {item.category} · confidence {item.confidence.toFixed(2)} · evidence{" "}
                {item.evidence_count}
              </span>
              <p className="muted">
                First {item.first_observed} · Last {item.last_observed}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
