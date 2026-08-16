import { useState } from "react";

type ChatResponse = {
  preview: { would_send: unknown; can_send: boolean; blocked_reason: string | null };
  answer: string | null;
  left_the_machine: boolean;
  remote_disabled: boolean;
  label: string;
};

export function ChatPage() {
  const [label, setLabel] = useState<string | null>(null);
  const [answer, setAnswer] = useState<string | null>(null);

  async function run(previewOnly: boolean) {
    const response = await fetch("/external/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer local-dev-token",
      },
      body: JSON.stringify({
        prompt: "What actually matters?",
        summary: "Review proposal before Friday",
        entities: ["PERSON_A4F91C"],
        may_transmit_remotely: true,
        preview_only: previewOnly,
        confirm_send: !previewOnly,
      }),
    });
    if (!response.ok) {
      setLabel(`Request failed (${response.status})`);
      setAnswer(null);
      return;
    }
    const data = (await response.json()) as ChatResponse;
    setLabel(data.label);
    setAnswer(data.answer);
  }

  return (
    <section className="page">
      <h1>Chat</h1>
      <p>
        Remote reasoning uses sanitised context only. Preview is on by default — confirm before
        anything leaves the machine.
      </p>
      <div className="cta-row">
        <button type="button" onClick={() => void run(true)}>
          Privacy preview
        </button>
        <button type="button" onClick={() => void run(false)}>
          Confirm send
        </button>
      </div>
      {label ? <p className="muted">{label}</p> : null}
      {answer ? <pre>{answer}</pre> : null}
    </section>
  );
}
