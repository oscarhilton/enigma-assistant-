import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  HONK_PROMPT,
  HONK_REPLY,
  HONK_RECOVERY_REPLY,
  HONK_SERIOUS_PROMPT,
  HONK_SERIOUS_REPLY,
} from "../pilot/WorldMockLifeScripts";
import { askV2Enigma, jumpV2DemoCheckpoint, launchV2AlexLab } from "./v2ProductHelpers";

describe("UI2-06 HONK HONK Life Script (v2 shell)", () => {
  it("recognition → abstinence → frame suppression → recovery through the shell", async () => {
    await launchV2AlexLab();
    await jumpV2DemoCheckpoint(/Jan 19 · 10:00/);

    await askV2Enigma(HONK_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(HONK_REPLY)).toBeInTheDocument();
    });
    expect(screen.queryByText(/feeling playful|metaphor|🦆/i)).not.toBeInTheDocument();
    let goose = await screen.findByTestId("surface-goose");
    expect(goose).toHaveAttribute("data-expressiveness", "playful");

    await askV2Enigma(HONK_SERIOUS_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(HONK_SERIOUS_REPLY)).toBeInTheDocument();
    });
    expect(screen.queryByText(/feeling playful|metaphor|🦆/i)).not.toBeInTheDocument();
    goose = screen.getByTestId("surface-goose");
    expect(goose).toHaveAttribute("data-expressiveness", "restrained");

    await askV2Enigma(HONK_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(HONK_RECOVERY_REPLY)).toBeInTheDocument();
    });
    goose = screen.getByTestId("surface-goose");
    expect(goose).toHaveAttribute("data-expressiveness", "playful");
  });
});
