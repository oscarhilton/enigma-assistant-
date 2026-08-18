import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Composer } from "./Composer";

describe("Composer", () => {
  it("keeps Dismiss out of the alert text so a 409 URL is not copied as *Dismiss", () => {
    render(
      <Composer
        error="HTTP 409 http://localhost:5173/demo/conversation"
        onDismissError={vi.fn()}
        onSend={async () => undefined}
      />,
    );
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("HTTP 409 http://localhost:5173/demo/conversation");
    expect(alert.textContent).not.toMatch(/Dismiss/);
    expect(alert.textContent).not.toMatch(/conversationDismiss/);
    expect(screen.getByRole("button", { name: /^dismiss$/i })).toBeInTheDocument();
  });
});
