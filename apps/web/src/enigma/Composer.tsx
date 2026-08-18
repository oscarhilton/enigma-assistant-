import { FormEvent, useState } from "react";

type Props = {
  onSend: (text: string) => Promise<void>;
  disabled?: boolean;
  busy?: boolean;
  error?: string | null;
  onDismissError?: () => void;
};

export function Composer({
  onSend,
  disabled = false,
  busy: externalBusy = false,
  error = null,
  onDismissError,
}: Props) {
  const [text, setText] = useState("");
  const [localBusy, setLocalBusy] = useState(false);
  const busy = externalBusy || localBusy;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || busy || disabled) {
      return;
    }
    setLocalBusy(true);
    try {
      await onSend(trimmed);
      setText("");
    } finally {
      setLocalBusy(false);
    }
  }

  return (
    <div className="composer-wrap">
      {error ? (
        <p className="composer-error" role="alert">
          {error}
          {onDismissError ? (
            <button type="button" className="composer-error-dismiss" onClick={onDismissError}>
              Dismiss
            </button>
          ) : null}
        </p>
      ) : null}
      <form className="composer" onSubmit={(event) => void handleSubmit(event)} aria-busy={busy}>
        <label className="sr-only" htmlFor="enigma-composer">
          Ask Enigma
        </label>
        <input
          id="enigma-composer"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Ask Enigma…"
          disabled={disabled || busy}
        />
        <button type="submit" disabled={disabled || busy || !text.trim()}>
          {busy ? "Sending…" : "Send"}
        </button>
      </form>
    </div>
  );
}
