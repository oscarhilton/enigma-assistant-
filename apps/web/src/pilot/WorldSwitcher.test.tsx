import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WorldProvider } from "./WorldProvider";
import { WorldSwitcher } from "./WorldSwitcher";

describe("WorldSwitcher", () => {
  it("lists Alex Lab and My Enigma in one control", () => {
    render(
      <WorldProvider initialWorld="my_enigma">
        <WorldSwitcher />
      </WorldProvider>,
    );
    const select = screen.getByTestId("world-switcher");
    expect(select).toHaveValue("my_enigma");
    expect(screen.getByRole("option", { name: "My Enigma" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Alex Lab" })).toBeInTheDocument();
    fireEvent.change(select, { target: { value: "alex_lab" } });
    expect(select).toHaveValue("alex_lab");
  });
});
