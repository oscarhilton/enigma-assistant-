import { describe, expect, it } from "vitest";
import {
  P03_MONDAY_PROMPT,
  P03_MONDAY_REPLY,
  P03_TOMORROW_PROMPT,
  P03_TOMORROW_REPLY,
  P03_WEEKEND_PROMPT,
  P03_WEEKEND_REPLY,
} from "./WorldMockCalendar";
import { askEnigma, launchMyEnigma, switchWorld } from "./pilotProductHelpers";
import { screen, waitFor } from "@testing-library/react";

describe("P03 calendar READ pilot scripts (My Enigma shell)", () => {
  it("Tomorrow — what am I doing tomorrow?", async () => {
    await launchMyEnigma();
    await askEnigma(P03_TOMORROW_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(P03_TOMORROW_REPLY)).toBeInTheDocument();
    });
    expect(screen.queryByText(/booking confirmed/i)).not.toBeInTheDocument();
  });

  it("Weekend — what's coming up this weekend?", async () => {
    await launchMyEnigma();
    await askEnigma(P03_WEEKEND_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(P03_WEEKEND_REPLY)).toBeInTheDocument();
    });
  });

  it("Availability — am I free Monday?", async () => {
    await launchMyEnigma();
    await askEnigma(P03_MONDAY_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(P03_MONDAY_REPLY)).toBeInTheDocument();
    });
  });
});

describe("P03 calendar world isolation", () => {
  it("calendar conversation does not leak into Alex Lab after switch", async () => {
    await launchMyEnigma();
    await askEnigma(P03_TOMORROW_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(P03_TOMORROW_REPLY)).toBeInTheDocument();
    });

    await switchWorld("alex_lab");
    expect(screen.queryByText(P03_TOMORROW_REPLY)).not.toBeInTheDocument();

    await switchWorld("my_enigma");
    expect(screen.queryByText(P03_TOMORROW_REPLY)).not.toBeInTheDocument();
  });
});
