import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "../App";

describe("V2Shell", () => {
  it("renders v2 shell with sidebar, world switcher, and build identity", async () => {
    render(
      <MemoryRouter initialEntries={["/v2"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByTestId("v2-shell")).toBeInTheDocument();
    expect(screen.getByTestId("v2-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("world-switcher")).toBeInTheDocument();
    expect(screen.getByTestId("v2-build-identity").textContent).toMatch(/^Enigma v2 · /);
    expect(screen.getByTestId("v2-composer-input")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
    });
  });

  it("does not replace v1 pilot shell at /", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByTestId("pilot-shell")).toBeInTheDocument();
    expect(screen.queryByTestId("v2-shell")).not.toBeInTheDocument();
  });
});
