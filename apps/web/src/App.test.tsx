import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("renders the product name", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText("personal-enigma")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /what actually matters/i })).toBeInTheDocument();
  });
});
