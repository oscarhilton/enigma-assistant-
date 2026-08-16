import { Link } from "react-router-dom";

export function DemoOverviewPage() {
  return (
    <section className="page demo-page">
      <h1>Demo Mode</h1>
      <p>
        Scripted walkthrough: start on day one (almost empty), advance through weeks of
        evidence, then check Attention for open loops. Banner stays visible — fictional
        data only; ground truth never appears in this chrome.
      </p>
      <p className="demo-walkthrough-hint">
        Operator path: <code>scenarios/product-demo</code> · see{" "}
        <code>docs/demo/walkthrough.md</code>
      </p>
      <p className="muted">
        Timeline controls sit above: Next event / Next day step manually; speed 1×–100×
        auto-plays (Pause stops). Open Attention while the clock runs to watch the list
        update.
      </p>
      <ul className="demo-overview-links">
        <li>
          <Link to="/demo/attention">Attention dashboard</Link>
        </li>
        <li>
          <Link to="/demo/memory">Memory browser</Link>
        </li>
        <li>
          <Link to="/demo/attention">Why view (open from an attention item)</Link>
        </li>
        <li>
          <Link to="/demo/privacy">Privacy inspector hook</Link>
        </li>
        <li className="demo-dev-link">
          <Link to="/demo/suppressed">Developer: suppressed signals</Link>
        </li>
      </ul>
    </section>
  );
}
