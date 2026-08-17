import type { QualificationDebug } from "../types";

type Props = {
  debug: QualificationDebug;
};

export function QualificationDebugView({ debug }: Props) {
  return (
    <section className="qualification-debug" data-testid="qualification-debug">
      <h3>Qualification debug</h3>
      <p>
        Composite {debug.composite_score.toFixed(3)} vs surface threshold{" "}
        {debug.surface_threshold.toFixed(2)} → {debug.policy_decision}
      </p>
      <table>
        <tbody>
          <tr>
            <th>actionability_now</th>
            <td>{debug.actionability_now.toFixed(2)}</td>
          </tr>
          <tr>
            <th>time_sensitivity</th>
            <td>{debug.time_sensitivity.toFixed(2)}</td>
          </tr>
          <tr>
            <th>calendar_boost</th>
            <td>{debug.calendar_boost.toFixed(2)}</td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}
