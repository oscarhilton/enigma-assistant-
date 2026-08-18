import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  HONK_PROMPT,
  HONK_REPLY,
  HONK_RECOVERY_REPLY,
  HONK_SERIOUS_PROMPT,
  HONK_SERIOUS_REPLY,
} from "./WorldMockLifeScripts";
import { askEnigma, jumpDemoCheckpoint, launchAlexLab } from "./pilotProductHelpers";

describe("P02c HONK HONK Life Script (pilot shell)", () => {
  it("recognition → abstinence → frame suppression → recovery through the shell", async () => {
    await launchAlexLab();
    await jumpDemoCheckpoint(/Jan 19 · 10:00/);

    await askEnigma(HONK_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(HONK_REPLY)).toBeInTheDocument();
    });
    expect(screen.queryByText(/feeling playful|metaphor|🦆/i)).not.toBeInTheDocument();
    let goose = await screen.findByTestId("surface-goose");
    expect(goose).toHaveAttribute("data-expressiveness", "playful");

    await askEnigma(HONK_SERIOUS_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(HONK_SERIOUS_REPLY)).toBeInTheDocument();
    });
    expect(screen.queryByText(/feeling playful|metaphor|🦆/i)).not.toBeInTheDocument();
    goose = screen.getByTestId("surface-goose");
    expect(goose).toHaveAttribute("data-expressiveness", "restrained");

    await askEnigma(HONK_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(HONK_RECOVERY_REPLY)).toBeInTheDocument();
    });
    goose = screen.getByTestId("surface-goose");
    expect(goose).toHaveAttribute("data-expressiveness", "playful");
  });
});
