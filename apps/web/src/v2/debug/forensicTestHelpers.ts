import { fireEvent, screen, waitFor } from "@testing-library/react";
import { expect, vi } from "vitest";
import { buildCopyBundle, parseCopyBundle } from "./copyBundles";
import { NOT_CAPTURED, type CopyTier, type ForensicModel } from "./types";

export async function openV2ForensicDebug() {
  fireEvent.keyDown(window, { key: "D", metaKey: true, shiftKey: true });
  await screen.findByTestId("v2-debug-panel");
}

export function assertStreamingAndMemoryHonest() {
  expect(screen.getByTestId("section-streaming-trace-unavailable")).toHaveTextContent(NOT_CAPTURED);
  expect(screen.getByTestId("section-memory-unavailable")).toHaveTextContent(NOT_CAPTURED);
}

export function assertUnavailableWhenEmpty(section: string) {
  const status = screen.getByTestId(`${section}-status`);
  if (status.textContent === "Unavailable") {
    expect(screen.getByTestId(`${section}-unavailable`)).toHaveTextContent(NOT_CAPTURED);
  }
}

export function assertWireOnlySectionsHonest() {
  for (const section of [
    "section-turn-contract",
    "section-relational-bootstrap",
    "section-handoff",
    "section-authority",
  ]) {
    assertUnavailableWhenEmpty(section);
  }
  assertStreamingAndMemoryHonest();
}

export function assertForensicSnapshotBar() {
  const bar = screen.getByTestId("v2-turn-snapshot");
  expect(bar).toHaveTextContent(/Build/i);
  expect(bar).toHaveTextContent(/World/i);
  expect(bar).toHaveTextContent(/Turn/i);
}

export function expectForensicHeader(text: string, privacy: "SAFE" | "DETAILED" | "LOCAL") {
  const lines = text.split("\n");
  expect(lines[0]).toBe("ENIGMA FORENSIC SNAPSHOT");
  expect(lines[1]).toMatch(/^Build: /);
  expect(lines[2]).toMatch(/^World: /);
  expect(lines[3]).toMatch(/^Turn: /);
  expect(lines[4]).toBe(`Privacy level: ${privacy}`);
}

export async function copyForensicBundle(tier: CopyTier): Promise<string> {
  const sectionsTab = screen.getByRole("tab", { name: "Sections" });
  sectionsTab.focus();
  fireEvent.keyDown(sectionsTab, { key: "ArrowRight" });
  const copyTab = await waitFor(() => {
    const tab = screen.getByRole("tab", { name: "Copy bundles" });
    expect(tab).toHaveAttribute("aria-selected", "true");
    return tab;
  });
  expect(copyTab).toHaveAttribute("aria-selected", "true");
  const writeText = navigator.clipboard.writeText as ReturnType<typeof vi.fn>;
  writeText.mockClear();
  fireEvent.click(await screen.findByTestId(`copy-bundle-${tier}`));
  await waitFor(() => {
    expect(writeText).toHaveBeenCalled();
  });
  return writeText.mock.calls.at(-1)![0] as string;
}

export function assertDetailedBundleDiagnosable(bundleText: string, lastUserPrompt: string) {
  expectForensicHeader(bundleText, "DETAILED");
  const parsed = parseCopyBundle(bundleText) as {
    user_input: { text: string };
    turn_contract: string;
    relational_bootstrap: string;
    handoff: string;
    streaming_trace: string;
    memory: string;
    agent_work: { exists: boolean };
  };
  expect(parsed.user_input.text).toBe(lastUserPrompt);
  if (parsed.turn_contract === NOT_CAPTURED) {
    expect(bundleText).not.toContain("grantsAuthority");
  }
  expect(parsed.handoff).toBe(NOT_CAPTURED);
  expect(parsed.streaming_trace).toBe(NOT_CAPTURED);
  expect(parsed.memory).toBe(NOT_CAPTURED);
  expect(parsed.agent_work).toBeDefined();
}

/** Build bundle from model without UI — for unit-level section checks. */
export function assertModelCopyTiers(model: ForensicModel) {
  for (const [tier, privacy] of [
    ["safe", "SAFE"],
    ["detailed", "DETAILED"],
    ["local", "LOCAL"],
  ] as const) {
    const text = buildCopyBundle(model, tier);
    expectForensicHeader(text, privacy);
    expect(() => parseCopyBundle(text)).not.toThrow();
  }
}
