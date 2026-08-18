import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { ALEX_CASE_ID, ALEX_CONVERSATION_CANARY, ALEX_SIMULATED_TIME } from "./WorldMockClient";

const PRIVATE_CANARY = "PRIVATE_CONVERSATION_MUST_NOT_LEAK";

function renderPilot(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

async function waitForWorldReady() {
  await waitFor(() => {
    expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
  });
}

async function switchWorld(world: "alex_lab" | "my_enigma") {
  fireEvent.change(screen.getByTestId("world-switcher"), { target: { value: world } });
  await waitFor(() => {
    expect(screen.getByTestId("world-switcher")).toHaveValue(world);
    expect(screen.getByTestId("pilot-shell")).toHaveAttribute("data-world", world);
  });
  await waitForWorldReady();
}

describe("P01 world isolation freeze", () => {
  it("WORLD_SWITCH_01 — private conversation does not appear in Alex after switch", async () => {
    renderPilot();
    await waitForWorldReady();
    const input = screen.getByPlaceholderText(/ask enigma/i);
    fireEvent.change(input, { target: { value: PRIVATE_CANARY } });
    fireEvent.click(screen.getByRole("button", { name: /^send$/i }));
    await waitFor(() => {
      expect(screen.getByText(PRIVATE_CANARY)).toBeInTheDocument();
    });

    await switchWorld("alex_lab");
    expect(screen.queryByText(PRIVATE_CANARY)).not.toBeInTheDocument();
    expect(screen.getByText(ALEX_CONVERSATION_CANARY)).toBeInTheDocument();
  });

  it("WORLD_SWITCH_02 — Alex conversation does not appear in private", async () => {
    renderPilot();
    await waitForWorldReady();
    await switchWorld("alex_lab");
    expect(screen.getByText(ALEX_CONVERSATION_CANARY)).toBeInTheDocument();

    await switchWorld("my_enigma");
    expect(screen.queryByText(ALEX_CONVERSATION_CANARY)).not.toBeInTheDocument();
  });

    it("CLOCK_01 — Alex clock chrome does not remain after switch to private", async () => {
    renderPilot();
    await waitForWorldReady();
    await switchWorld("alex_lab");
    await waitFor(() => {
      expect(screen.getByText(/Demo ·/)).toBeInTheDocument();
    });

    await switchWorld("my_enigma");
    expect(screen.queryByText(/Demo ·/)).not.toBeInTheDocument();
    expect(screen.queryByText(new RegExp(ALEX_SIMULATED_TIME.slice(0, 10)))).not.toBeInTheDocument();
  });

  it("GOOSE_01 — switching worlds cannot leave stale AgentWork projected by Goose", async () => {
    renderPilot();
    await waitForWorldReady();
    await switchWorld("alex_lab");
    const goose = await screen.findByTestId("surface-goose");
    expect(goose).toHaveAttribute("data-motion", "return");
    fireEvent.click(screen.getByRole("button", { name: /explain checked why this matters/i }));
    await waitFor(() => {
      expect(screen.getByTestId("work-explanation")).toBeInTheDocument();
    });

    await switchWorld("my_enigma");
    expect(screen.queryByTestId("surface-goose")).not.toBeInTheDocument();
    expect(screen.queryByTestId("work-explanation")).not.toBeInTheDocument();
  });

  it("CASE_01 — case selected in world A cannot remain selected as if valid in B", async () => {
    renderPilot("/cases");
    await waitForWorldReady();
    await switchWorld("alex_lab");
    fireEvent.click(screen.getByRole("link", { name: /^cases$/i }));
    const select = await screen.findByTestId(`select-case-${ALEX_CASE_ID}`);
    fireEvent.click(select);
    expect(screen.getByTestId("selected-case")).toHaveAttribute("data-case-id", ALEX_CASE_ID);

    await switchWorld("my_enigma");
    expect(screen.queryByTestId("selected-case")).not.toBeInTheDocument();
    expect(screen.queryByTestId(`select-case-${ALEX_CASE_ID}`)).not.toBeInTheDocument();
    expect(screen.getByText(/this world has none yet/i)).toBeInTheDocument();
  });
});
