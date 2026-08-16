import { useOutletContext } from "react-router-dom";
import { AttentionDashboard } from "./AttentionDashboard";
import type { DemoOutletContext } from "./DemoLayout";

export function DemoAttentionPage() {
  const { status } = useOutletContext<DemoOutletContext>();

  return (
    <section className="page demo-page">
      <h1>Attention dashboard</h1>
      <AttentionDashboard simulatedTime={status?.simulated_time} />
    </section>
  );
}
