import { Link, useNavigate } from "react-router-dom";
import { GoosePresence } from "../enigma/GoosePresence";
import { inspectGooseEvent, projectGooseEvents, recordGooseTelemetry } from "../enigma/gooseTelemetry";
import { WorldSwitcher } from "../pilot/WorldSwitcher";
import { useWorld } from "../pilot/WorldProvider";
import { useCallback, useEffect, useRef, useState } from "react";
import type { GoosePixelLicence } from "../enigma/goosePixels";
import { buildIdentityLabel } from "./buildIdentity";
import { useDebugShortcut } from "./debug/useDebugShortcut";
import { V2Composer } from "./V2Composer";
import { V2ConversationViewport } from "./V2ConversationViewport";
import { V2Sidebar } from "./V2Sidebar";
import { useV2Threads } from "./V2ThreadProvider";
import { useV2StreamingConversation } from "./useV2StreamingConversation";

export function V2Shell() {
  const navigate = useNavigate();
  const { world } = useWorld();
  const {
    activeThread,
    updateActiveThreadItems,
    renameActiveThreadFromMessage,
  } = useV2Threads();
  const {
    items,
    streamingRow,
    loading,
    busy,
    error,
    disconnected,
    generationStopped,
    sendMessage,
    cancel,
    reconnect,
    clearError,
    gooseLicence,
    client,
  } = useV2StreamingConversation({
    threadItems: activeThread.items,
    onThreadItemsChange: updateActiveThreadItems,
    onFirstMessage: renameActiveThreadFromMessage,
  });
  const [workExplanation, setWorkExplanation] = useState<string[]>([]);
  const previousGooseLicence = useRef<GoosePixelLicence | null>(null);

  const openDebug = useCallback(() => {
    void navigate("/v2/debug");
  }, [navigate]);
  useDebugShortcut(openDebug);

  useEffect(() => {
    recordGooseTelemetry(projectGooseEvents(previousGooseLicence.current, gooseLicence));
    previousGooseLicence.current = gooseLicence;
  }, [gooseLicence]);

  function inspectGooseWork() {
    recordGooseTelemetry([inspectGooseEvent(gooseLicence)]);
    const target = gooseLicence.inspectTarget;
    if (target) {
      void client.getProvenance(target).catch(() => {
        setWorkExplanation(gooseLicence.inspectLabels);
      });
      return;
    }
    setWorkExplanation(gooseLicence.inspectLabels);
  }

  return (
    <div className="v2-root v2-shell" data-testid="v2-shell" data-world={world}>
      <header className="v2-header">
        <strong className="text-sm font-semibold tracking-tight">Enigma</strong>
        <div className="v2-chrome-tools">
          <div className="v2-world-switcher">
            <WorldSwitcher />
          </div>
          <GoosePresence licence={gooseLicence} onInspect={inspectGooseWork} />
        </div>
      </header>

      <V2Sidebar />

      <main className="v2-main">
        <V2ConversationViewport items={items} loading={loading} streamingRow={streamingRow} />
        {workExplanation.length > 0 ? (
          <section
            className="px-4 pb-2 text-sm text-muted-foreground"
            data-testid="v2-work-explanation"
            aria-label="Work explanation"
          >
            <ul className="list-disc pl-5">
              {workExplanation.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </section>
        ) : null}
        <V2Composer
          onSend={sendMessage}
          onCancel={cancel}
          onReconnect={reconnect}
          disabled={loading}
          busy={busy}
          disconnected={disconnected}
          generationStopped={generationStopped}
          error={error}
          onDismissError={clearError}
        />
      </main>

      <footer className="v2-footer">
        <span data-testid="v2-build-identity">{buildIdentityLabel()}</span>
        <Link to="/v2/debug" className="hover:underline">
          Debug
        </Link>
      </footer>
    </div>
  );
}
