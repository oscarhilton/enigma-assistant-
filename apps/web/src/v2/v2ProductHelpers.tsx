import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";
import { clearThreadStorage } from "./threadStorage";

export async function launchV2AlexLab(path = "/v2") {
  clearThreadStorage("alex_lab");
  clearThreadStorage("my_enigma");
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
  await waitFor(() => {
    expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
  });
  fireEvent.change(screen.getByTestId("world-switcher"), { target: { value: "alex_lab" } });
  await waitFor(() => {
    expect(screen.getByTestId("v2-shell")).toHaveAttribute("data-world", "alex_lab");
    expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
  });
}

export async function jumpV2DemoCheckpoint(label: RegExp) {
  fireEvent.click(screen.getByRole("button", { name: /Demo ·/i }));
  await screen.findByText(/Time machine/i);
  const buttons = await screen.findAllByRole("button", { name: label });
  const checkpoint =
    buttons.find((button) => button.hasAttribute("aria-pressed")) ?? buttons[buttons.length - 1]!;
  fireEvent.click(checkpoint);
  await waitFor(() => {
    expect(screen.getByTestId("v2-attention-surface")).toBeInTheDocument();
  });
}

export async function askV2Enigma(text: string) {
  const input = screen.getByTestId("v2-composer-input");
  fireEvent.change(input, { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: /^send$/i }));
}

export async function switchV2World(world: "alex_lab" | "my_enigma") {
  fireEvent.change(screen.getByTestId("world-switcher"), { target: { value: world } });
  await waitFor(() => {
    expect(screen.getByTestId("world-switcher")).toHaveValue(world);
    expect(screen.getByTestId("v2-shell")).toHaveAttribute("data-world", world);
  });
  await waitFor(() => {
    expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
  });
}
