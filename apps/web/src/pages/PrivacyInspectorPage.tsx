import { useState } from "react";

type InspectionResult = {
  would_send: Record<string, unknown> | null;
  privacy_level: string;
  redactions: { field: string; reason: string }[];
  apple_permission_note: string;
  can_send: boolean;
  blocked_reason: string | null;
  cancelled: boolean;
};

const demoPayload = {
  summary: "Review the proposal before Friday's meeting",
  entities: ["PERSON_A1"],
  may_transmit_remotely: true,
  source_type: "reminder",
  remote_enabled: true,
};

export function PrivacyInspectorPage() {
  const [result, setResult] = useState<InspectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function inspect(cancel: boolean) {
    setError(null);
    try {
      const response = await fetch("/privacy/inspect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...demoPayload, cancel }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      setResult((await response.json()) as InspectionResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to inspect");
      setResult({
        would_send: cancel
          ? null
          : { summary: demoPayload.summary, entities: demoPayload.entities },
        privacy_level: "medium",
        redactions: [],
        apple_permission_note:
          "Revoking Calendar, Reminders, Contacts, or Notes in System Settings stops new ingestion.",
        can_send: !cancel,
        blocked_reason: cancel ? "User cancelled remote send" : null,
        cancelled: cancel,
      });
    }
  }

  return (
    <section className="page">
      <h1>Privacy inspector</h1>
      <p>Preview what would be sent remotely. The inspector itself does not upload.</p>
      <div className="cta-row">
        <button type="button" onClick={() => void inspect(false)}>
          Preview remote payload
        </button>
        <button type="button" onClick={() => void inspect(true)}>
          Cancel remote send
        </button>
      </div>
      {error ? <p className="muted">API unavailable — showing local preview ({error})</p> : null}
      {result ? (
        <div className="inspector-panel">
          <p>
            Privacy level: <strong>{result.privacy_level}</strong>
          </p>
          <p>Can send: {result.can_send ? "yes" : "no"}</p>
          {result.blocked_reason ? <p>Blocked: {result.blocked_reason}</p> : null}
          <h2>Would send</h2>
          <pre>{JSON.stringify(result.would_send, null, 2)}</pre>
          <h2>Redactions</h2>
          <ul>
            {result.redactions.map((r) => (
              <li key={r.field}>
                {r.field}: {r.reason}
              </li>
            ))}
          </ul>
          <p className="muted">{result.apple_permission_note}</p>
        </div>
      ) : null}
    </section>
  );
}
