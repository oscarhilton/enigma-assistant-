import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  BRUNCH_BOOKED_DISTINCTION,
  BRUNCH_TITLE,
} from "../../pilot/WorldMockClient";
import {
  FORGET_PROMPT,
  HONK_PROMPT,
  HONK_REPLY,
  MAYA_OPENING_PROMPT,
  MAYA_OPENING_REPLY,
  VERIFICATION_OUTCOME_PROMPT,
  VERIFICATION_PREPARE_PROMPT,
  VERIFICATION_FAILURE_REPLY,
} from "../../pilot/WorldMockLifeScripts";
import { NOT_CAPTURED } from "./types";
import {
  assertDetailedBundleDiagnosable,
  assertForensicSnapshotBar,
  assertWireOnlySectionsHonest,
  copyForensicBundle,
  openV2ForensicDebug,
} from "./forensicTestHelpers";
import { askV2Enigma, jumpV2DemoCheckpoint, launchV2AlexLab } from "../v2ProductHelpers";
import { fireEvent } from "@testing-library/react";

describe("UI2-06 Life Script forensic snapshots", () => {
  beforeEach(() => {
    vi.stubGlobal("navigator", {
      ...navigator,
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  async function captureForensicsAfterScript(
    lastPrompt: string,
    beforeCopy?: () => void,
  ): Promise<string> {
    await openV2ForensicDebug();
    assertForensicSnapshotBar();
    assertWireOnlySectionsHonest();
    expect(screen.getByTestId("section-user-input-status")).toHaveTextContent("Wired");
    expect(screen.getByTestId("section-user-input")).toHaveTextContent(lastPrompt);
    beforeCopy?.();
    const bundle = await copyForensicBundle("detailed");
    assertDetailedBundleDiagnosable(bundle, lastPrompt);
    expect(bundle).not.toContain("privateperson");
    expect(bundle).not.toContain("grantsAuthority");
    return bundle;
  }

  it("Brunch — forensic snapshot diagnoses calendar hold ≠ booking after turn", async () => {
    await launchV2AlexLab();
    await jumpV2DemoCheckpoint(/Jan 20 · 11:00/);
    expect(screen.getByText(BRUNCH_TITLE)).toBeInTheDocument();

    await askV2Enigma("what did I book?");
    await waitFor(() => {
      expect(screen.getByText(BRUNCH_BOOKED_DISTINCTION)).toBeInTheDocument();
    });

    await captureForensicsAfterScript("what did I book?", () => {
      expect(screen.getByTestId("section-not-disclosed-status")).toHaveTextContent("Wired");
      expect(screen.getByTestId("section-agent-work-status")).toHaveTextContent("Wired");
    });
  });

  it("Monday/Maya — forensic snapshot captures challenge turn without inventing wire-only fields", async () => {
    await launchV2AlexLab();
    await jumpV2DemoCheckpoint(/Jan 19 · 10:00/);

    await askV2Enigma(MAYA_OPENING_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(MAYA_OPENING_REPLY)).toBeInTheDocument();
    });

    await captureForensicsAfterScript(MAYA_OPENING_PROMPT, () => {
      expect(screen.getByTestId("section-evidence-status")).toHaveTextContent("Wired");
    });
  });

  it("HONK HONK — forensic snapshot shows agent work continuity across playful turn", async () => {
    await launchV2AlexLab();
    await jumpV2DemoCheckpoint(/Jan 19 · 10:00/);

    await askV2Enigma(HONK_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(HONK_REPLY)).toBeInTheDocument();
    });

    await captureForensicsAfterScript(HONK_PROMPT, () => {
      expect(screen.getByTestId("section-agent-work-status")).toHaveTextContent("Wired");
      expect(screen.getByTestId("section-agent-work")).toHaveTextContent(/phase|semantic/i);
    });
  });

  it("FALSE VICTORY — forensic snapshot does not imply success when verification fails", async () => {
    await launchV2AlexLab();
    await jumpV2DemoCheckpoint(/Jan 19 · 10:00/);

    await askV2Enigma(VERIFICATION_PREPARE_PROMPT);
    await waitFor(() => {
      expect(screen.getByTestId("assist-proposal")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /^approve$/i }));
    await waitFor(() => {
      expect(screen.getByText(/sending the note now/i)).toBeInTheDocument();
    });

    await askV2Enigma(VERIFICATION_OUTCOME_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(VERIFICATION_FAILURE_REPLY)).toBeInTheDocument();
    });
    expect(screen.getByTestId("assist-result").className).toMatch(/error/);

    const bundle = await captureForensicsAfterScript(VERIFICATION_OUTCOME_PROMPT, () => {
      expect(screen.getByTestId("section-agent-work-status")).toHaveTextContent("Wired");
    });
    expect(bundle.toLowerCase()).not.toMatch(/successfully completed|job succeeded/);
  });

  it("Forget — forensic snapshot honest after forget turn (no resurrection in bundle)", async () => {
    await launchV2AlexLab();
    await jumpV2DemoCheckpoint(/Jan 19 · 10:00/);

    await askV2Enigma("Maya mentioned she likes ceramics.");
    await waitFor(() => {
      expect(screen.getByText(/remember Maya likes ceramics/i)).toBeInTheDocument();
    });

    await askV2Enigma(FORGET_PROMPT);
    await waitFor(() => {
      expect(screen.getByText(/drop that retained memory/i)).toBeInTheDocument();
    });

    await captureForensicsAfterScript(FORGET_PROMPT, () => {
      expect(screen.getByTestId("section-memory-unavailable")).toHaveTextContent(NOT_CAPTURED);
    });
  });
});
