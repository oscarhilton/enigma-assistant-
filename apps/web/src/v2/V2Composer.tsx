import { FormEvent, useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

type Props = {
  onSend: (text: string) => Promise<boolean | void>;
  onCancel?: () => void;
  onReconnect?: () => Promise<void> | void;
  disabled?: boolean;
  busy?: boolean;
  disconnected?: boolean;
  error?: string | null;
  onDismissError?: () => void;
};

/** Bottom composer — streaming send, Stop cancel, Reconnect after drop. */
export function V2Composer({
  onSend,
  onCancel,
  onReconnect,
  disabled = false,
  busy = false,
  disconnected = false,
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
      const ok = await onSend(trimmed);
      if (ok !== false) {
        setText("");
      }
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
        {sending ? (
          <Button
            type="button"
            variant="outline"
            data-testid="v2-composer-stop"
            onClick={() => onCancel?.()}
          >
            Stop
          </Button>
        ) : (
          <Button type="submit" disabled={disabled || !text.trim()}>
            Send
          </Button>
        )}
        {disconnected ? (
          <Button
            type="button"
            variant="secondary"
            data-testid="v2-composer-reconnect"
            onClick={() => void onReconnect?.()}
          >
            Reconnect
          </Button>
        ) : null}
      </form>
    </div>
  );
}
