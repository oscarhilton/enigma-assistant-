import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Composer } from "../enigma/Composer";
import { ConversationViewport } from "../enigma/ConversationViewport";
import { DemoControlsPanel } from "../enigma/DemoControlsPanel";
import { EgressDisclosurePanel } from "../enigma/EgressDisclosurePanel";
import { EnigmaProvider, useEnigmaConversation } from "../enigma/EnigmaProvider";
import { GoosePresence } from "../enigma/GoosePresence";
import { licenceFromConversation, type GoosePixelLicence } from "../enigma/goosePixels";
import { inspectGooseEvent, projectGooseEvents, recordGooseTelemetry } from "../enigma/gooseTelemetry";
import { ProvenanceViewPanel } from "../enigma/items/ProvenanceViewPanel";
import { QualificationDebugView } from "../enigma/items/QualificationDebugView";
import type { ProvenanceView, QualificationDebug } from "../enigma/types";

function ConversationalHomeInner() {
  const {
    items,
    attention,
    loading,
    busy,
    error,
    clearError,
    sendMessage,
    approveAssist,
    client,
  } = useEnigmaConversation();
  const [provenance, setProvenance] = useState<ProvenanceView | null>(null);
  const [debug, setDebug] = useState<QualificationDebug | null>(null);
  const [showUnderBonnet, setShowUnderBonnet] = useState(false);
  const [workExplanation, setWorkExplanation] = useState<string[]>([]);
  const gooseLicence = useMemo(
    () => licenceFromConversation({ items, busy, loading }),
    [items, busy, loading],
  );
  const previousGooseLicence = useRef<GoosePixelLicence | null>(null);

  useEffect(() => {
    recordGooseTelemetry(projectGooseEvents(previousGooseLicence.current, gooseLicence));
    previousGooseLicence.current = gooseLicence;
  }, [gooseLicence]);

  function inspectGooseWork() {
    recordGooseTelemetry([inspectGooseEvent(gooseLicence)]);
    const target = gooseLicence.inspectTarget;
    if (target) {
      void client
        .getProvenance(target)
        .then(setProvenance)
        .catch(() => {
          setWorkExplanation(gooseLicence.inspectLabels);
        });
      return;
    }
    setWorkExplanation(gooseLicence.inspectLabels);
  }

  return (
    <section className="page conversational-home">
      <header className="conversational-header">
        <div className="conversational-header-identity">
          <div>
            <h1>Enigma</h1>
            <p>World state is truth — not chat history.</p>
          </div>
          <GoosePresence licence={gooseLicence} onInspect={inspectGooseWork} />
        </div>
        <DemoControlsPanel
          client={client}
          checkpointId={attention?.checkpoint_id}
          simulatedTime={attention?.simulated_time}
          proactiveSilence={attention?.presentation.proactive_silence ?? false}
          showUnderBonnet={showUnderBonnet}
          onShowUnderBonnetChange={setShowUnderBonnet}
          items={items}
        />
      </header>

      <ConversationViewport
        items={items}
        loading={loading}
        demoMode={client.isDemo()}
        showUnderBonnet={showUnderBonnet && client.isDemo()}
        onWhy={(itemId) => {
          void client.getProvenance(itemId).then(setProvenance);
        }}
        onQualificationDebug={(itemId) => {
          void client.getQualificationDebug(itemId).then(setDebug);
        }}
        onHelpAssist={() => {
          void sendMessage("Can you help me do that?");
        }}
        onApproveAssist={approveAssist}
      />

      {provenance ? <ProvenanceViewPanel provenance={provenance} /> : null}
      {workExplanation.length > 0 ? (
        <section className="work-explanation" data-testid="work-explanation" aria-label="Work explanation">
          <ul>
            {workExplanation.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {debug ? <QualificationDebugView debug={debug} /> : null}

      <Composer
        onSend={sendMessage}
        disabled={loading}
        busy={busy}
        error={error}
        onDismissError={clearError}
      />

      <nav className="under-bonnet" aria-label="Under the bonnet">
        <Link to="/demo/memory">Memory</Link>
        <Link to="/demo/privacy">Privacy</Link>
        <Link to="/settings">Settings</Link>
      </nav>

      <EgressDisclosurePanel client={client} />
    </section>
  );
}

export function HomePage() {
  return (
    <EnigmaProvider>
      <ConversationalHomeInner />
    </EnigmaProvider>
  );
}
