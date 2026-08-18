import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("renders one pilot shell with world switcher, Today, Cases, and Ask Enigma", async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("pilot-shell")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^enigma$/i })).toBeInTheDocument();
    expect(screen.getByTestId("world-switcher")).toHaveValue("my_enigma");
    expect(screen.getByRole("link", { name: /^today$/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^cases$/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/ask enigma/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
    });
    expect(screen.queryByTestId("surface-goose")).not.toBeInTheDocument();
  });

  it("switches worlds inside the same shell", async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("today-surface")).toBeInTheDocument();
    });
    fireEvent.change(screen.getByTestId("world-switcher"), { target: { value: "alex_lab" } });
    expect(screen.getByTestId("world-switcher")).toHaveValue("alex_lab");
    expect(screen.getAllByTestId("pilot-shell")).toHaveLength(1);
    expect(screen.getByPlaceholderText(/ask enigma/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("conversation-viewport")).toBeInTheDocument();
    });
  });

  it("Cases is the same product shell, not a second app", async () => {
    render(
      <MemoryRouter initialEntries={["/cases"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("pilot-shell")).toBeInTheDocument();
    expect(screen.getByTestId("cases-surface")).toBeInTheDocument();
    expect(screen.getByTestId("world-switcher")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/ask enigma/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByTestId("surface-goose")).not.toBeInTheDocument();
    });
  });
});
