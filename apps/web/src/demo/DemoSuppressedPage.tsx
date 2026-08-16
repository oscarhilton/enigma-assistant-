import { SuppressionInspector } from "./SuppressionInspector";

export function DemoSuppressedPage() {
  return (
    <section className="page demo-page">
      <h1>Suppressed signals</h1>
      <SuppressionInspector />
    </section>
  );
}
