import { Link } from "react-router-dom";

/**
 * Demo chrome hook into the shared Privacy Inspector (M17).
 * Does not duplicate inspector logic — only deep-links and framing.
 */
export function PrivacyInspectorHook() {
  return (
    <section className="demo-panel" aria-label="Privacy inspector hook">
      <h2>Privacy</h2>
      <p>
        Preview what a remote model would see for demo context. The inspector itself does not
        upload; ground truth stays off the default demo chrome.
      </p>
      <div className="cta-row">
        <Link className="demo-link-button" to="/privacy">
          Open privacy inspector
        </Link>
        <span className="muted">Asks: what did the remote model see?</span>
      </div>
    </section>
  );
}
