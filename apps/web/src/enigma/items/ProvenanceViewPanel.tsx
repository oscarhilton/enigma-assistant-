import type { ProvenanceView as ProvenanceType } from "../types";

type Props = {
  provenance: ProvenanceType;
};

export function ProvenanceViewPanel({ provenance }: Props) {
  return (
    <section className="provenance-panel">
      <h3>{provenance.headline}</h3>
      <ul>
        {provenance.why_now.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </section>
  );
}
