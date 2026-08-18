import { useState } from "react";
import { Link } from "react-router-dom";
import { ConversationViewport } from "../enigma/ConversationViewport";
import { DemoControlsPanel } from "../enigma/DemoControlsPanel";
import { EgressDisclosurePanel } from "../enigma/EgressDisclosurePanel";
import { useEnigmaConversation } from "../enigma/EnigmaProvider";
import { ProvenanceViewPanel } from "../enigma/items/ProvenanceViewPanel";
import { QualificationDebugView } from "../enigma/items/QualificationDebugView";
import type { ProvenanceView, QualificationDebug } from "../enigma/types";

export function HomePage() {
  const { items, attention, loading, sendMessage, approveAssist, client } = useEnigmaConversation();
  const [provenance, setProvenance] = useState<ProvenanceView | null>(null);
  const [debug, setDebug] = useState<QualificationDebug | null>(null);
  const [showUnderBonnet, setShowUnderBonnet] = useState(false);

  return (
    <section className="page conversational-home" data-testid="today-surface">
      {client.isDemo() ? (
        <header className="conversational-header">
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
      ) : null}

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
      {debug ? <QualificationDebugView debug={debug} /> : null}

      <nav className="under-bonnet" aria-label="Under the bonnet">
        <Link to="/demo/memory">Memory</Link>
        <Link to="/demo/privacy">Privacy</Link>
        <Link to="/settings">Settings</Link>
      </nav>

      <EgressDisclosurePanel client={client} />
    </section>
  );
}
