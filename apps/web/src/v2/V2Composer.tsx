import { FormEvent, useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

type Props = {
  onSend: (text: string) => Promise<void>;
  disabled?: boolean;
  busy?: boolean;
  error?: string | null;
  onDismissError?: () => void;
};

/** Bottom composer — structured for streaming send/cancel in UI2-02. */
export function V2Composer({
  onSend,
  disabled = false,
  busy = false,
  error = null,
  onDismissError,
}: Props) {
  const [text, setText] = useState("");
  const [localBusy, setLocalBusy] = useState(false);
  const sending = busy || localBusy;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || sending || disabled) {
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
    <div className="v2-composer" data-testid="v2-composer">
      {error ? (
        <p className="mb-2 text-sm text-destructive" role="alert">
          {error}
          {onDismissError ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="ml-2 h-auto p-0 text-destructive"
              onClick={onDismissError}
            >
              Dismiss
            </Button>
          ) : null}
        </p>
      ) : null}
      <form
        className="flex gap-2 max-w-3xl mx-auto"
        onSubmit={(event) => void handleSubmit(event)}
        aria-busy={sending}
      >
        <label className="sr-only" htmlFor="v2-composer-input">
          Message Enigma
        </label>
        <Input
          id="v2-composer-input"
          data-testid="v2-composer-input"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Message Enigma…"
          disabled={disabled || sending}
          className="flex-1"
        />
        <Button type="submit" disabled={disabled || sending || !text.trim()}>
          {sending ? "Sending…" : "Send"}
        </Button>
      </form>
    </div>
  );
}
