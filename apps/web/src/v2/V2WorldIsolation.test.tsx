import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { ALEX_CASE_ID, ALEX_CONVERSATION_CANARY, ALEX_SIMULATED_TIME } from "../pilot/WorldMockClient";
import { clearThreadStorage } from "./threadStorage";
import { switchV2World } from "./v2ProductHelpers";

async function waitForWorldReady() {
  await waitFor(() => {
    expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
  });
}

describe("UI2-06 world isolation (v2 shell)", () => {
  it("GOOSE_01 — switching worlds cannot leave stale AgentWork projected by Goose", async () => {
    clearThreadStorage("alex_lab");
    clearThreadStorage("my_enigma");
    render(
      <MemoryRouter initialEntries={["/v2"]}>
        <App />
      </MemoryRouter>,
    );
    await waitForWorldReady();
    await switchV2World("alex_lab");
    const goose = await screen.findByTestId("surface-goose");
    expect(goose).toHaveAttribute("data-motion", "return");
    fireEvent.click(screen.getByRole("button", { name: /explain checked why this matters/i }));
    await waitFor(() => {
      expect(screen.getByTestId("v2-work-explanation")).toBeInTheDocument();
    });

    await switchV2World("my_enigma");
    expect(screen.queryByTestId("surface-goose")).not.toBeInTheDocument();
    expect(screen.queryByTestId("v2-work-explanation")).not.toBeInTheDocument();
  });

  it("CASE_01 — case selected in world A cannot remain selected as if valid in B", async () => {
    clearThreadStorage("alex_lab");
    clearThreadStorage("my_enigma");
    render(
      <MemoryRouter initialEntries={["/v2/cases"]}>
        <App />
      </MemoryRouter>,
    );
    await waitForWorldReady();
    await switchV2World("alex_lab");
    const select = await screen.findByTestId(`select-case-${ALEX_CASE_ID}`);
    fireEvent.click(select);
    expect(screen.getByTestId("selected-case")).toHaveAttribute("data-case-id", ALEX_CASE_ID);

    await switchV2World("my_enigma");
    expect(screen.queryByTestId("selected-case")).not.toBeInTheDocument();
    expect(screen.queryByTestId(`select-case-${ALEX_CASE_ID}`)).not.toBeInTheDocument();
    expect(screen.getByText(/this world has none yet/i)).toBeInTheDocument();
  });

  it("CLOCK_01 — Alex demo chrome does not remain after switch to private", async () => {
    clearThreadStorage("alex_lab");
    clearThreadStorage("my_enigma");
    render(
      <MemoryRouter initialEntries={["/v2"]}>
        <App />
      </MemoryRouter>,
    );
    await waitForWorldReady();
    await switchV2World("alex_lab");
    await waitFor(() => {
      expect(screen.getByText(/Demo ·/)).toBeInTheDocument();
    });

    await switchV2World("my_enigma");
    expect(screen.queryByText(/Demo ·/)).not.toBeInTheDocument();
    expect(screen.queryByText(new RegExp(ALEX_SIMULATED_TIME.slice(0, 10)))).not.toBeInTheDocument();
  });

  it("WORLD_SWITCH — Alex canary does not leak into private thread", async () => {
    clearThreadStorage("alex_lab");
    clearThreadStorage("my_enigma");
    render(
      <MemoryRouter initialEntries={["/v2"]}>
        <App />
      </MemoryRouter>,
    );
    await waitForWorldReady();
    await switchV2World("alex_lab");
    await waitFor(() => {
      expect(screen.getByTestId("v2-message-assistant")).toHaveTextContent(ALEX_CONVERSATION_CANARY);
    });

    await switchV2World("my_enigma");
    const assistant = screen.queryByTestId("v2-message-assistant");
    if (assistant) {
      expect(assistant).not.toHaveTextContent(ALEX_CONVERSATION_CANARY);
    }
  });
});
