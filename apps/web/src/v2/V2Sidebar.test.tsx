import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { EnigmaProvider } from "../enigma/EnigmaProvider";
import { WorldProvider } from "../pilot/WorldProvider";
import { clearThreadStorage } from "./threadStorage";
import { V2Sidebar } from "./V2Sidebar";
import { V2ThreadProvider } from "./V2ThreadProvider";

function renderSidebar() {
  return render(
    <MemoryRouter>
      <WorldProvider>
        <EnigmaProvider>
          <V2ThreadProvider>
            <V2Sidebar />
          </V2ThreadProvider>
        </EnigmaProvider>
      </WorldProvider>
    </MemoryRouter>,
  );
}

describe("V2Sidebar", () => {
  beforeEach(() => {
    clearThreadStorage("my_enigma");
    clearThreadStorage("alex_lab");
  });

  it("lists threads and highlights the active one", () => {
    renderSidebar();
    expect(screen.getByTestId("v2-thread-list")).toBeInTheDocument();
    const active = screen.getByTestId("v2-thread-list").querySelector('[data-active="true"]');
    expect(active).not.toBeNull();
    expect(active).toHaveTextContent("New chat");
  });

  it("creates a new thread when New chat is clicked", () => {
    renderSidebar();
    const initialCount = screen.getAllByRole("button", { name: /new chat/i }).length;
    fireEvent.click(screen.getByTestId("v2-new-chat"));
    expect(screen.getAllByText("New chat").length).toBeGreaterThan(initialCount);
  });

  it("selects a different thread from the list", () => {
    renderSidebar();
    fireEvent.click(screen.getByTestId("v2-new-chat"));
    const threads = screen.getAllByRole("button").filter((node) => node.dataset.testid?.startsWith("v2-thread-"));
    expect(threads.length).toBeGreaterThanOrEqual(2);
    const second = threads[1];
    expect(second).toBeDefined();
    fireEvent.click(second!);
    expect(second).toHaveAttribute("data-active", "true");
  });
});
