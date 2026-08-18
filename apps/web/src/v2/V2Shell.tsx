import { Link, NavLink, Outlet } from "react-router-dom";
import { GoosePresence } from "../enigma/GoosePresence";
import { inspectGooseEvent, projectGooseEvents, recordGooseTelemetry } from "../enigma/gooseTelemetry";
import { DemoControlsPanel } from "../enigma/DemoControlsPanel";
import { useEnigmaConversation } from "../enigma/EnigmaProvider";
import { ProvenanceViewPanel } from "../enigma/items/ProvenanceViewPanel";
import type { ProvenanceView } from "../enigma/types";
import { WorldSwitcher } from "../pilot/WorldSwitcher";
import { useWorld } from "../pilot/WorldProvider";
import { useEffect, useRef, useState } from "react";
import type { GoosePixelLicence } from "../enigma/goosePixels";
import { buildIdentityLabel } from "./buildIdentity";
import { V2Composer } from "./V2Composer";
import { V2Sidebar } from "./V2Sidebar";
import { useV2Threads } from "./V2ThreadProvider";
import { useV2StreamingConversation } from "./useV2StreamingConversation";

export type V2OutletContext = {
  items: ReturnType<typeof useV2StreamingConversation>["items"];
  streamingRow: ReturnType<typeof useV2StreamingConversation>["streamingRow"];
  loading: boolean;
  demoMode: boolean;
  onWhy: (itemId: string) => void;
  onApproveAssist: (proposalId: string) => Promise<void>;
  onHelpAssist: () => void;
};

export function V2Shell() {
  const { world } = useWorld();
  const session = useEnigmaConversation();
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
  const [provenance, setProvenance] = useState<ProvenanceView | null>(null);
  const previousGooseLicence = useRef<GoosePixelLicence | null>(null);

  useEffect(() => {
    recordGooseTelemetry(projectGooseEvents(previousGooseLicence.current, gooseLicence));
    previousGooseLicence.current = gooseLicence;
  }, [gooseLicence]);

  useEffect(() => {
    setProvenance(null);
    setWorkExplanation([]);
  }, [world]);

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

  function handleWhy(itemId: string) {
    void client.getProvenance(itemId).then(setProvenance);
  }

  return (
    <div className="v2-root v2-shell" data-testid="v2-shell" data-world={world}>
      <header className="v2-header">
        <strong className="text-sm font-semibold tracking-tight">Enigma</strong>
        <nav className="v2-nav flex gap-3 text-sm" aria-label="v2 daily">
          <NavLink to="/v2" end className={({ isActive }) => (isActive ? "font-semibold" : "")}>
            Chat
          </NavLink>
          <NavLink to="/v2/cases" className={({ isActive }) => (isActive ? "font-semibold" : "")}>
            Cases
          </NavLink>
        </nav>
        <div className="v2-chrome-tools">
          <div className="v2-world-switcher">
            <WorldSwitcher />
          </div>
          <GoosePresence licence={gooseLicence} onInspect={inspectGooseWork} />
        </div>
      </header>

      <V2Sidebar />

      <main className="v2-main">
        {client.isDemo() ? (
          <div className="v2-demo-bar px-v2-3 pt-v2-2">
            <DemoControlsPanel
              client={client}
              checkpointId={session.attention?.checkpoint_id}
              simulatedTime={session.attention?.simulated_time}
              proactiveSilence={session.attention?.presentation.proactive_silence ?? false}
              items={items}
            />
          </div>
        ) : null}
        <Outlet
          context={{
            items,
            streamingRow,
            loading,
            demoMode: client.isDemo(),
            onWhy: handleWhy,
            onApproveAssist: session.approveAssist,
            onHelpAssist: () => void sendMessage("Can you help me do that?"),
          }}
        />
        {provenance ? (
          <section className="px-v2-4 pb-v2-2" data-testid="v2-provenance">
            <ProvenanceViewPanel provenance={provenance} />
          </section>
        ) : null}
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
