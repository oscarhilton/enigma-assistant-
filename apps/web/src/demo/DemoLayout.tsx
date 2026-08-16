import { useCallback, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import type { DemoStatus } from "./api";
import { SimulationStatus } from "./SimulationStatus";
import { TimelineControls } from "./TimelineControls";

/**
 * Demo chrome shell: nav + timeline controls + simulation status around nested routes.
 * Persistent DEMO MODE banner is owned by App (forced active on `/demo/*`).
 */
export function DemoLayout() {
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const onStatusChange = useCallback((next: DemoStatus) => {
    setStatus(next);
  }, []);

  return (
    <div className="demo-shell">
      <nav className="demo-nav" aria-label="Demo">
        <NavLink to="/demo" end>
          Overview
        </NavLink>
        <NavLink to="/demo/attention">Attention</NavLink>
        <NavLink to="/demo/memory">Memory</NavLink>
        <NavLink to="/demo/privacy">Privacy</NavLink>
      </nav>
      <div className="demo-grid">
        <TimelineControls onStatusChange={onStatusChange} />
        <SimulationStatus status={status} />
      </div>
      <Outlet />
    </div>
  );
}
