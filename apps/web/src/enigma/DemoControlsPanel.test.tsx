import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DemoControlsPanel } from "./DemoControlsPanel";
import type { EnigmaClient } from "./client";
import { formatLastTurnDump, formatSessionDump } from "./forensicDump";
import { MOCK_ATTENTION_JAN19, MOCK_LLM_TRACE_LLM, MOCK_LLM_TRACE_ROUTER } from "./fixtures";
import type { ConversationItem, DemoEvent } from "./types";

const writeText = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  writeText.mockClear();
  Object.assign(navigator, { clipboard: { writeText } });
});

const TRACE_ITEMS: ConversationItem[] = [
  {
    kind: "user_message",
    at: MOCK_ATTENTION_JAN19.simulated_time,
    text: "What should I do next?",
  },
  {
    kind: "next_action",
    at: MOCK_ATTENTION_JAN19.simulated_time,
    action: MOCK_ATTENTION_JAN19.next_actions[0]!,
    llm_trace: MOCK_LLM_TRACE_ROUTER,
  },
  {
    kind: "user_message",
    at: MOCK_ATTENTION_JAN19.simulated_time,
    text: "Why do I need to do this?",
  },
  {
    kind: "enigma_message",
    at: MOCK_ATTENTION_JAN19.simulated_time,
    text: "Because the token inventory is unblocked.",
    llm_trace: MOCK_LLM_TRACE_LLM,
  },
];

function makeDemoClient(overrides: Partial<EnigmaClient> = {}): EnigmaClient {
  const handlers = new Set<(event: import("./events").EnigmaEvent) => void>();
  return {
    isDemo: () => true,
    subscribe: (handler) => {
      handlers.add(handler);
      return () => handlers.delete(handler);
    },
    listCheckpoints: vi.fn().mockResolvedValue([
      { id: "cp-jan19", at: "2026-01-19T10:00:00+00:00", label: "Jan 19 · 10:00" },
      { id: "cp-jan20", at: "2026-01-20T10:00:00+00:00", label: "Jan 20 · 10:00" },
    ]),
    getDemoEvents: vi.fn().mockResolvedValue([
      {
        kind: "proactive_silence",
        at: "2026-01-19T10:00:00+00:00",
        proactive_silence: true,
      } satisfies DemoEvent,
    ]),
    jumpCheckpoint: vi.fn().mockResolvedValue(undefined),
    getConversation: vi.fn(),
    sendMessage: vi.fn(),
    getAttentionState: vi.fn(),
    getQualificationDebug: vi.fn(),
    getProvenance: vi.fn(),
    proposeAssist: vi.fn(),
    approveAssist: vi.fn(),
    getRecentDisclosures: vi.fn().mockResolvedValue([]),
    ...overrides,
  };
}

describe("DemoControlsPanel", () => {
  it("shows silence hint and refreshes events after checkpoint jump", async () => {
    const client = makeDemoClient();
    render(
      <DemoControlsPanel
        client={client}
        checkpointId="cp-jan19"
        proactiveSilence
      />,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /jan 19/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /silent/i }));
    expect(screen.getByTestId("demo-silence-hint")).toHaveTextContent(/proactive silence/i);

    fireEvent.click(screen.getByRole("button", { name: /^Jan 20/i }));
    await waitFor(() => {
      expect(client.jumpCheckpoint).toHaveBeenCalledWith("cp-jan20");
    });
    await waitFor(() => {
      expect(client.getDemoEvents).toHaveBeenCalledTimes(2);
    });
  });

  it("toggles show under the bonnet from the demo header", async () => {
    const onShowUnderBonnetChange = vi.fn();
    const client = makeDemoClient();
    render(
      <DemoControlsPanel
        client={client}
        checkpointId="cp-jan19"
        showUnderBonnet={false}
        onShowUnderBonnetChange={onShowUnderBonnetChange}
      />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("under-bonnet-toggle")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("under-bonnet-toggle"));
    expect(onShowUnderBonnetChange).toHaveBeenCalledWith(true);
  });

  it("disables copy buttons until a turn has an llm_trace", async () => {
    const client = makeDemoClient();
    render(<DemoControlsPanel client={client} checkpointId="cp-jan19" items={[]} />);

    await waitFor(() => {
      expect(screen.getByTestId("copy-debug")).toBeDisabled();
    });
    expect(screen.getByTestId("copy-last-turn")).toBeDisabled();
  });

  it("copies the full forensic session dump next to under the bonnet", async () => {
    const client = makeDemoClient();
    render(
      <DemoControlsPanel client={client} checkpointId="cp-jan19" items={TRACE_ITEMS} />,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^copy debug$/i })).toBeEnabled();
    });
    expect(screen.getByRole("button", { name: /^copy last turn$/i })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: /^copy debug$/i }));
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(
        formatSessionDump([MOCK_LLM_TRACE_ROUTER, MOCK_LLM_TRACE_LLM]),
      );
    });
    expect(await screen.findByRole("button", { name: /^copied$/i })).toBeInTheDocument();
  });

  it("copies only the latest turn", async () => {
    const client = makeDemoClient();
    render(
      <DemoControlsPanel client={client} checkpointId="cp-jan19" items={TRACE_ITEMS} />,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^copy last turn$/i })).toBeEnabled();
    });

    fireEvent.click(screen.getByRole("button", { name: /^copy last turn$/i }));
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(formatLastTurnDump([MOCK_LLM_TRACE_ROUTER, MOCK_LLM_TRACE_LLM]));
    });
  });
});
