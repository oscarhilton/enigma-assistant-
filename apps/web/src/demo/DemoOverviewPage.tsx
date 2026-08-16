import { useState } from "react";
import { Link } from "react-router-dom";
import { SimulationStatus } from "./SimulationStatus";
import { TimelineControls } from "./TimelineControls";
import type { DemoStatus } from "./types";

export function DemoOverviewPage() {
  const [status, setStatus] = useState<DemoStatus | null>(null);

  return (
    <section className="page demo-page">
      <h1>Demo Mode</h1>
      <p>
        Walk a fictional life through the real Enigma pipeline. Timeline controls advance
        simulated time; attention and memory stay free of ground-truth overlays.
      </p>
      <TimelineControls onStatusChange={setStatus} />
      <SimulationStatus status={status} />
      <ul className="demo-overview-links">
        <li>
          <Link to="/demo/attention">Attention dashboard</Link>
        </li>
        <li>
          <Link to="/demo/memory">Memory browser</Link>
        </li>
        <li>
          <Link to="/demo/why/att-atlas-review">Why view</Link>
        </li>
        <li>
          <Link to="/demo/privacy">Privacy inspector hook</Link>
        </li>
      </ul>
    </section>
  );
}
