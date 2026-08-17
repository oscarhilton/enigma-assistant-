import { useState } from "react";
import type { AssistProposal } from "../types";

type Props = {
  proposal: AssistProposal;
  onApprove?: (proposalId: string) => void | Promise<void>;
  approved?: boolean;
};

export function AssistProposalView({ proposal, onApprove, approved = false }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const disabled = approved || busy || !onApprove;

  async function handleApprove() {
    if (disabled) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onApprove(proposal.id);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "Approval failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="assist-proposal" data-testid="assist-proposal">
      <h3>{proposal.title}</h3>
      <p>{proposal.description}</p>
      {error ? (
        <p className="assist-proposal-error" role="alert">
          {error}
        </p>
      ) : null}
      <button type="button" onClick={() => void handleApprove()} disabled={disabled}>
        {approved ? "Approved" : busy ? "Approving…" : proposal.action_label}
      </button>
    </article>
  );
}
