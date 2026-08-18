import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { App } from "../../App";
import { useDebugShortcut } from "./useDebugShortcut";

describe("V2DebugPanel", () => {
  it("renders semantic forensics sections at /v2/debug", async () => {
    render(
      <MemoryRouter initialEntries={["/v2/debug"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("v2-debug-panel")).toBeInTheDocument();
    expect(screen.getByTestId("v2-turn-snapshot")).toBeInTheDocument();
    expect(screen.getByTestId("section-user-input")).toBeInTheDocument();
    expect(screen.getByTestId("section-turn-contract")).toBeInTheDocument();
    expect(screen.getByTestId("section-evidence")).toBeInTheDocument();
    expect(screen.getByTestId("section-not-disclosed")).toBeInTheDocument();
    expect(screen.getByTestId("section-relational-bootstrap")).toBeInTheDocument();
    expect(screen.getByTestId("section-handoff")).toBeInTheDocument();
    expect(screen.getByTestId("section-agent-work")).toBeInTheDocument();
    expect(screen.getByTestId("section-authority")).toBeInTheDocument();
    expect(screen.getByTestId("section-remote-payload")).toBeInTheDocument();
    expect(screen.getByTestId("section-streaming-trace")).toBeInTheDocument();
    expect(screen.getByTestId("section-memory")).toBeInTheDocument();
  });

  it("⌘⇧D opens debug route from v2 shell", async () => {
    render(
      <MemoryRouter initialEntries={["/v2"]}>
        <App />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("v2-shell")).toBeInTheDocument();
    });

    fireEvent.keyDown(window, { key: "D", metaKey: true, shiftKey: true });

    expect(await screen.findByTestId("v2-debug-panel")).toBeInTheDocument();
  });
});

describe("useDebugShortcut", () => {
  it("invokes callback on meta+shift+d without breaking default handling when prevented", () => {
    const onOpen = vi.fn();
    function Harness() {
      useDebugShortcut(onOpen);
      return <input data-testid="composer" />;
    }

    render(<Harness />);
    const input = screen.getByTestId("composer");
    input.focus();

    fireEvent.keyDown(window, { key: "d", metaKey: true, shiftKey: true });
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(document.activeElement).toBe(input);
  });
});
