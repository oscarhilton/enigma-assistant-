import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConversationViewport } from "./ConversationViewport";
import { MOCK_ATTENTION_JAN19, MOCK_LLM_TRACE_LLM, MOCK_LLM_TRACE_ROUTER } from "./fixtures";

describe("ConversationViewport", () => {
  it("renders structured attention summary items", () => {
    render(
      <ConversationViewport
        items={[
          {
            kind: "attention_summary",
            at: MOCK_ATTENTION_JAN19.simulated_time,
            state: MOCK_ATTENTION_JAN19,
          },
        ]}
        demoMode
      />,
    );
    expect(screen.getByTestId("conversation-viewport")).toBeInTheDocument();
    expect(screen.getByText(/nothing needs you/i)).toBeInTheDocument();
  });

  it("renders a next-action-only turn without attention buckets", () => {
    const action = MOCK_ATTENTION_JAN19.next_actions[0]!;
    render(
      <ConversationViewport
        items={[{ kind: "next_action", at: MOCK_ATTENTION_JAN19.simulated_time, action }]}
        onHelpAssist={() => {}}
      />,
    );
    expect(screen.getByText(action.title)).toBeInTheDocument();
    expect(screen.getByText(/^Unblocked now$/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /help me do this/i })).toBeInTheDocument();
    expect(screen.queryByText(/nothing needs you/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^NEEDS YOU$/)).not.toBeInTheDocument();
  });

  it("calls onHelpAssist when Help me do this is clicked on a next action", () => {
    const action = MOCK_ATTENTION_JAN19.next_actions[0]!;
    const onHelpAssist = vi.fn();
    render(
      <ConversationViewport
        items={[{ kind: "next_action", at: MOCK_ATTENTION_JAN19.simulated_time, action }]}
        onHelpAssist={onHelpAssist}
      />,
    );
    screen.getByRole("button", { name: /help me do this/i }).click();
    expect(onHelpAssist).toHaveBeenCalledOnce();
  });

  it("renders waiting-on attention items without next actions", () => {
    const brunch = MOCK_ATTENTION_JAN19.context[0]!;
    render(
      <ConversationViewport
        items={[
          {
            kind: "attention_item",
            at: MOCK_ATTENTION_JAN19.simulated_time,
            item: brunch,
          },
        ]}
      />,
    );
    expect(screen.getByText(brunch.title)).toBeInTheDocument();
    expect(screen.getByText(/^CONTEXT$/)).toBeInTheDocument();
    expect(screen.queryByText(/^A good thing you could do:$/)).not.toBeInTheDocument();
  });

  it("renders an assist proposal with title and Approve", () => {
    const action = MOCK_ATTENTION_JAN19.next_actions[0]!;
    render(
      <ConversationViewport
        items={[
          {
            kind: "assist_proposal",
            at: MOCK_ATTENTION_JAN19.simulated_time,
            proposal: {
              id: "assist-token",
              title: action.title,
              description: "I'll record a synthetic demo draft for this.",
              action_label: "Approve",
            },
          },
        ]}
      />,
    );
    expect(screen.getByTestId("assist-proposal")).toBeInTheDocument();
    expect(screen.getByText(action.title)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^approve$/i })).toBeInTheDocument();
  });

  it("renders a world-just-loaded changed turn as copy only", () => {
    render(
      <ConversationViewport
        items={[
          {
            kind: "enigma_message",
            at: MOCK_ATTENTION_JAN19.simulated_time,
            text: "Nothing has changed — the world just loaded.",
          },
        ]}
      />,
    );
    expect(screen.getByText(/world just loaded/i)).toBeInTheDocument();
    expect(screen.queryByText(/token inventory/i)).not.toBeInTheDocument();
  });

  it("shows an empty-state prompt when there are no items", () => {
    render(<ConversationViewport items={[]} />);
    expect(screen.getByText(/ask enigma what needs you/i)).toBeInTheDocument();
  });

  it("shows a loading placeholder", () => {
    render(<ConversationViewport items={[]} loading />);
    expect(screen.getByText(/loading conversation/i)).toBeInTheDocument();
  });

  it("renders assist results with success styling", () => {
    render(
      <ConversationViewport
        items={[
          {
            kind: "assist_result",
            at: MOCK_ATTENTION_JAN19.simulated_time,
            proposal_id: "assist-brunch",
            ok: true,
            message: "Done — I recorded a synthetic draft.",
          },
        ]}
      />,
    );
    const result = screen.getByTestId("assist-result");
    expect(result).toHaveTextContent(/synthetic draft/i);
    expect(result.className).toMatch(/success/);
  });

  it("marks assist proposals approved after a successful result", () => {
    render(
      <ConversationViewport
        items={[
          {
            kind: "assist_proposal",
            at: MOCK_ATTENTION_JAN19.simulated_time,
            proposal: {
              id: "assist-brunch",
              title: "Book brunch",
              description: "Synthetic demo draft.",
              action_label: "Approve",
            },
          },
          {
            kind: "assist_result",
            at: MOCK_ATTENTION_JAN19.simulated_time,
            proposal_id: "assist-brunch",
            ok: true,
            message: "Done.",
          },
        ]}
      />,
    );
    expect(screen.getByRole("button", { name: /^approved$/i })).toBeDisabled();
  });

  it("shows a completed activity strip from llm_trace without under-bonnet", () => {
    render(
      <ConversationViewport
        demoMode
        items={[
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
        ]}
      />,
    );
    expect(screen.getByTestId("activity-strip")).toHaveTextContent("Checked why this matters");
    expect(screen.queryByTestId("turn-debug")).not.toBeInTheDocument();
  });

  it("hides under-bonnet expanders until enabled", () => {
    render(
      <ConversationViewport
        demoMode
        items={[
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
        ]}
      />,
    );
    expect(screen.queryByTestId("turn-debug")).not.toBeInTheDocument();
  });

  it("shows router vs LLM traces when under the bonnet is on", () => {
    render(
      <ConversationViewport
        demoMode
        showUnderBonnet
        items={[
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
        ]}
      />,
    );

    const traces = screen.getAllByTestId("turn-debug");
    expect(traces).toHaveLength(2);

    const routerTrace = traces[0]!;
    fireEvent.click(within(routerTrace).getByText("LLM trace"));
    expect(within(routerTrace).getByTestId("llm-trace-path")).toHaveTextContent("intent_router");
    expect(within(routerTrace).getByTestId("llm-trace-intent")).toHaveTextContent("next_action_query");
    expect(within(routerTrace).getByText(/none — router fallback/i)).toBeInTheDocument();
    expect(within(routerTrace).getByTestId("llm-trace-subject")).toHaveTextContent(
      "item-obligation_token_audit (next_action)",
    );

    fireEvent.click(within(routerTrace).getByText("Privacy disclosure"));
    expect(within(routerTrace).getByText(/no remote payload/i)).toBeInTheDocument();
    expect(within(routerTrace).getByText(/PRIVATE_RAW/)).toBeInTheDocument();
    expect(within(routerTrace).queryByText(/@/)).not.toBeInTheDocument();

    const llmTrace = traces[1]!;
    fireEvent.click(within(llmTrace).getByText("LLM trace"));
    expect(within(llmTrace).getByTestId("llm-trace-path")).toHaveTextContent("llm");
    expect(within(llmTrace).getByText(/"subject_id": "item-obligation_token_audit"/)).toBeInTheDocument();
    expect(within(llmTrace).getAllByText(/"name": "world.explain"/).length).toBeGreaterThan(0);
  });
});
