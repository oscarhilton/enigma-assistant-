import type { EvidenceBundle } from "./types";
import { courierLine, courierStateClass, deriveCourierState, deriveGooseState } from "./courier";

type Props = {
  bundle: EvidenceBundle;
  curious?: boolean;
};

export function EvidenceCourier({ bundle, curious = false }: Props) {
  const state = deriveCourierState(bundle);
  const gooseState = deriveGooseState(bundle);
  if (state === "resting") {
    return null;
  }

  const line = courierLine(bundle, state);
  if (!line) {
    return null;
  }

  const satchel = curious ? (
    <ul className="evidence-courier-satchel">
      {bundle.searched_sources.length > 0 ? (
        <li>Searched: {bundle.searched_sources.join(", ")}</li>
      ) : null}
      {bundle.empty_sources.length > 0 ? (
        <li>Empty: {bundle.empty_sources.join(", ")}</li>
      ) : null}
      {bundle.unsearched_sources.length > 0 ? (
        <li>Not searched: {bundle.unsearched_sources.join(", ")}</li>
      ) : null}
      {bundle.unavailable_sources.length > 0 ? (
        <li>Unavailable: {bundle.unavailable_sources.join(", ")}</li>
      ) : null}
      {bundle.grounded_assertions.length > 0 ? (
        <li>Assertions: {bundle.grounded_assertions.map((row) => `${row.subject}.${row.predicate}`).join(", ")}</li>
      ) : null}
      {bundle.unknowns.length > 0 ? (
        <li>Unknowns: {bundle.unknowns.map((row) => `${row.predicate} (${row.reason})`).join(", ")}</li>
      ) : null}
    </ul>
  ) : null;

  if (curious && satchel) {
    return (
      <details
        className={`evidence-courier ${courierStateClass(state)}`}
        data-testid="evidence-courier"
      >
        <summary>
          <span className="evidence-courier-icon" aria-hidden="true" data-goose-state={gooseState}>
            🪿
          </span>
          {line}
        </summary>
        {satchel}
      </details>
    );
  }

  return (
    <p className={`evidence-courier ${courierStateClass(state)}`} data-testid="evidence-courier">
      <span className="evidence-courier-icon" aria-hidden="true" data-goose-state={gooseState}>
        🪿
      </span>
      {line}
    </p>
  );
}
