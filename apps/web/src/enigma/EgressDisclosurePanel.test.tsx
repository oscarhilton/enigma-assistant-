import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { EnigmaClient } from "./client";
import { DisclosureUnavailableError } from "./disclosureFetch";
import { EgressDisclosurePanel } from "./EgressDisclosurePanel";
import { C09_TOOL_NAMES, MOCK_DISCLOSURES } from "./fixtures";

function mockClient(rows = MOCK_DISCLOSURES): EnigmaClient {
  return {
    getConversation: vi.fn(),
    sendMessage: vi.fn(),
    getAttentionState: vi.fn(),
    getQualificationDebug: vi.fn(),
    getProvenance: vi.fn(),
    proposeAssist: vi.fn(),
    approveAssist: vi.fn(),
    jumpCheckpoint: vi.fn(),
    listCheckpoints: vi.fn(),
    getDemoEvents: vi.fn(),
    getRecentDisclosures: vi.fn().mockResolvedValue(rows),
    subscribe: vi.fn(() => () => undefined),
    isDemo: vi.fn(() => false),
  };
}

function openPanel() {
  fireEvent.click(screen.getByRole("button", { name: /what left my machine\?/i }));
}

function expandRow(testId: string) {
  const row = screen.getByTestId(testId);
  fireEvent.click(row.querySelector("summary") as HTMLElement);
  return row;
}

describe("EgressDisclosurePanel", () => {
  it("loads and lists disclosures when opened", async () => {
    const client = mockClient();
    render(<EgressDisclosurePanel client={client} />);

    openPanel();

    expect(await screen.findByTestId("disclosure-disc-mock-orchestrate")).toBeInTheDocument();
    expect(screen.getByTestId("disclosure-disc-mock-blocked")).toBeInTheDocument();
    expect(client.getRecentDisclosures).toHaveBeenCalledOnce();
    expect(screen.getByText(/^Sent$/)).toBeInTheDocument();
    expect(screen.getByText(/^Blocked$/)).toBeInTheDocument();
    expect(screen.getAllByText(/Fireworks \//i).length).toBeGreaterThan(0);
  });

  it("summary tab uses precise privacy wording and included/excluded lists", async () => {
    render(<EgressDisclosurePanel client={mockClient()} />);
    openPanel();
    await screen.findByTestId("disclosure-disc-mock-orchestrate");
    const row = expandRow("disclosure-disc-mock-orchestrate");

    const summary = within(row).getByTestId("disclosure-tab-summary");
    expect(summary).toHaveTextContent(
      /No raw source content was included\. Email bodies, calendar descriptions, contact details and private world records were not transmitted\./,
    );
    expect(summary).not.toHaveTextContent(/no raw private content crosses this boundary/i);
    expect(summary).toHaveTextContent(/current user message/);
    expect(summary).toHaveTextContent(/raw email bodies/);
    expect(summary).toHaveTextContent(/world\.explain/);
    expect(summary).toHaveTextContent(/gmail\.search/);
    expect(summary).not.toHaveTextContent("get_attention_state");
    expect(within(row).getByTestId("disclosure-context-manifest")).toHaveTextContent(
      "PRIVATE_QUERY",
    );
    expect(within(row).getByTestId("disclosure-context-manifest-json").textContent).toContain(
      "justification",
    );
  });

  it("exact outbound payload tab shows the wire JSON, not only the summary", async () => {
    render(<EgressDisclosurePanel client={mockClient()} />);
    openPanel();
    await screen.findByTestId("disclosure-disc-mock-orchestrate");
    const row = expandRow("disclosure-disc-mock-orchestrate");

    fireEvent.click(within(row).getByRole("tab", { name: /exact outbound payload/i }));
    const exact = within(row).getByTestId("disclosure-outbound-payload");
    expect(exact.textContent).toContain("Why do I need to do this?");
    expect(exact.textContent).toContain("item-obligation_token_audit");
    expect(exact.textContent).toContain("world.explain");
    expect(exact).not.toHaveTextContent("get_attention_state");
    expect(exact.textContent).not.toMatch(/api[_-]?key/i);
    for (const name of C09_TOOL_NAMES) {
      expect(exact.textContent).toContain(`"name": "${name}"`);
    }
  });

  it("tool trace tab reconstructs the correlation chain", async () => {
    render(<EgressDisclosurePanel client={mockClient()} />);
    openPanel();
    await screen.findByTestId("disclosure-disc-mock-orchestrate");
    const row = expandRow("disclosure-disc-mock-orchestrate");

    expect(within(row).getByTestId("disclosure-corr-disc-mock-orchestrate")).toHaveTextContent(
      "corr-demo-orchestrate-001",
    );
    fireEvent.click(within(row).getByRole("tab", { name: /tool trace/i }));
    const trace = within(row).getByTestId("disclosure-tool-trace");
    expect(trace).toHaveTextContent("corr-demo-orchestrate-001");
    expect(trace).toHaveTextContent("world.explain");
    expect(trace).toHaveTextContent(/"effect": "allowed"/);
  });

  it("shows block reason for rejected egress", async () => {
    render(<EgressDisclosurePanel client={mockClient()} />);
    openPanel();
    await screen.findByTestId("disclosure-disc-mock-blocked");

    expandRow("disclosure-disc-mock-blocked");

    expect(screen.getByText(/Remote inference disabled/i)).toBeInTheDocument();
    expect(screen.getByText(/"rejected_type": "PrivateRaw"/)).toBeInTheDocument();
  });

  it("shows an honest empty state when there are no disclosures", async () => {
    render(<EgressDisclosurePanel client={mockClient([])} />);
    openPanel();
    expect(await screen.findByTestId("egress-disclosure-empty")).toHaveTextContent(
      "No remote inference disclosures yet.",
    );
    expect(screen.queryByTestId("egress-disclosure-error")).not.toBeInTheDocument();
  });

  it("renders a readable HTML/non-JSON error, not a JSON.parse crash", async () => {
    const client = {
      ...mockClient([]),
      getRecentDisclosures: vi.fn().mockRejectedValue(
        new DisclosureUnavailableError({
          status: 200,
          received: "text/html",
          correlationId: "corr-test-html",
          preview: "<!doctype html>",
        }),
      ),
    };
    render(<EgressDisclosurePanel client={client} />);
    openPanel();

    const alert = await screen.findByTestId("egress-disclosure-error");
    expect(alert).toHaveTextContent("Privacy disclosure unavailable");
    expect(alert).toHaveTextContent("Expected application/json");
    expect(alert).toHaveTextContent("Received text/html");
    expect(alert).toHaveTextContent("HTTP 200");
    expect(alert).toHaveTextContent("Endpoint: /private/disclosure/recent");
    expect(alert).toHaveTextContent("Correlation: corr-test-html");
    expect(screen.getByTestId("egress-disclosure-error-preview")).toHaveTextContent("<!doctype html>");
    expect(alert).not.toHaveTextContent(/unexpected token/i);
    expect(screen.queryByTestId("egress-disclosure-empty")).not.toBeInTheDocument();
  });

  it("never surfaces a raw JSON.parse exception in the panel", async () => {
    const client = {
      ...mockClient([]),
      getRecentDisclosures: vi.fn().mockRejectedValue(
        new Error(`Unexpected token '<', "<!doctype "... is not valid JSON`),
      ),
    };
    render(<EgressDisclosurePanel client={client} />);
    openPanel();

    const alert = await screen.findByTestId("egress-disclosure-error");
    expect(alert).toHaveTextContent("Privacy disclosure unavailable");
    expect(alert).toHaveTextContent("Received text/html");
    expect(alert).not.toHaveTextContent(/unexpected token/i);
    expect(alert).not.toHaveTextContent(/is not valid JSON/i);
  });
});
