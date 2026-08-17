import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AssistProposalView } from "./AssistProposalView";

const PROPOSAL = {
  id: "assist-brunch",
  title: "Book Saturday brunch for Elena's parents",
  description: "I'll book this on the synthetic demo calendar.",
  action_label: "Approve",
};

describe("AssistProposalView", () => {
  it("renders title and Approve, and clicking Approve calls the client", async () => {
    const onApprove = vi.fn().mockResolvedValue(undefined);
    render(<AssistProposalView proposal={PROPOSAL} onApprove={onApprove} />);
    expect(screen.getByText(PROPOSAL.title)).toBeInTheDocument();
    const button = screen.getByRole("button", { name: /^approve$/i });
    fireEvent.click(button);
    expect(screen.getByRole("button", { name: /approving/i })).toBeDisabled();
    await waitFor(() => {
      expect(onApprove).toHaveBeenCalledTimes(1);
    });
    expect(onApprove).toHaveBeenCalledWith("assist-brunch");
  });

  it("shows an error when approval fails", async () => {
    const onApprove = vi.fn().mockRejectedValue(new Error("Network error"));
    render(<AssistProposalView proposal={PROPOSAL} onApprove={onApprove} />);
    fireEvent.click(screen.getByRole("button", { name: /^approve$/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/network error/i);
    });
  });
});
