import { Link } from "react-router-dom";

export function DemoOverviewPage() {
  return (
    <section className="page demo-overview">
      <h1>Demo Mode</h1>
      <p>
        Walk a fictional life through the real Enigma pipeline. Use timeline controls to step or
        advance days; explore attention, memory, and privacy without ever touching Private data.
      </p>
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
