import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";

export async function launchAlexLab(path = "/") {
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
    expect(screen.getByTestId("pilot-shell")).toHaveAttribute("data-world", "alex_lab");
    expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
  });
}

export async function launchMyEnigma(path = "/") {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
  await waitFor(() => {
    expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
    expect(screen.getByTestId("pilot-shell")).toHaveAttribute("data-world", "my_enigma");
  });
}

export async function jumpDemoCheckpoint(label: RegExp) {
  fireEvent.click(screen.getByRole("button", { name: /Demo ·/i }));
  await screen.findByText(/Time machine/i);
  const buttons = await screen.findAllByRole("button", { name: label });
  const checkpoint =
    buttons.find((button) => button.hasAttribute("aria-pressed")) ?? buttons[buttons.length - 1]!;
  fireEvent.click(checkpoint);
  await waitFor(() => {
    expect(screen.getByTestId("today-surface")).toBeInTheDocument();
  });
}

export async function askEnigma(text: string) {
  const input = screen.getByPlaceholderText(/ask enigma/i);
  fireEvent.change(input, { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: /^send$/i }));
}

export async function switchWorld(world: "alex_lab" | "my_enigma") {
  fireEvent.change(screen.getByTestId("world-switcher"), { target: { value: world } });
  await waitFor(() => {
    expect(screen.getByTestId("pilot-shell")).toHaveAttribute("data-world", world);
    expect(screen.queryByText(/Loading conversation/)).not.toBeInTheDocument();
  });
}
