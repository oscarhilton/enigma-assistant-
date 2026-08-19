import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { copyTextToClipboard } from "../../enigma/forensicDump";
import { useEnigmaConversation } from "../../enigma/EnigmaProvider";
import type { ProvenanceView } from "../../enigma/types";
import { useWorld } from "../../pilot/WorldProvider";
import { workSnapshotFromConversation } from "../../enigma/goosePixels";
import { buildForensicModel } from "./buildForensicModel";
import { buildCopyBundle } from "./copyBundles";
import type { CopyTier, ForensicModel } from "./types";
import { ForensicSectionCard } from "./ForensicSectionCard";
import { useStreamTrace } from "../StreamTraceProvider";
import { useV2Threads } from "../V2ThreadProvider";

function TurnSnapshotBar({
  model,
  onCopySnapshot,
  copied,
}: {
  model: ForensicModel;
  onCopySnapshot: () => void;
  copied: boolean;
}) {
  const { snapshot } = model;
  return (
    <div
      className="rounded-lg border border-border bg-muted/30 p-4"
      data-testid="v2-turn-snapshot"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Turn snapshot</p>
          <dl className="mt-2 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <dt className="text-muted-foreground">Build</dt>
              <dd className="font-mono text-xs">{snapshot.buildCommit}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">World</dt>
              <dd>{snapshot.worldLabel}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Time</dt>
              <dd className="font-mono text-xs">{snapshot.simulatedTime ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Turn</dt>
              <dd>
                {snapshot.turnIndex > 0 ? `${snapshot.turnIndex} / ${snapshot.turnCount}` : "—"}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-muted-foreground">Correlation</dt>
              <dd className="font-mono text-xs break-all">{snapshot.correlationId ?? "—"}</dd>
            </div>
          </dl>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          data-testid="copy-turn-snapshot"
          onClick={onCopySnapshot}
        >
          {copied ? "Copied" : "Copy turn snapshot"}
        </Button>
      </div>
    </div>
  );
}

function CopyBundles({ model }: { model: ForensicModel }) {
  const [copied, setCopied] = useState<CopyTier | null>(null);

  useEffect(() => {
    if (!copied) {
      return;
    }
    const id = window.setTimeout(() => setCopied(null), 1500);
    return () => window.clearTimeout(id);
  }, [copied]);

  async function copyTier(tier: CopyTier) {
    await copyTextToClipboard(buildCopyBundle(model, tier));
    setCopied(tier);
  }

  return (
    <div className="flex flex-wrap gap-2" data-testid="v2-copy-bundles">
      {(["safe", "detailed", "local"] as const).map((tier) => (
        <Button
          key={tier}
          type="button"
          variant="secondary"
          size="sm"
          data-testid={`copy-bundle-${tier}`}
          onClick={() => void copyTier(tier)}
        >
          {copied === tier ? "Copied" : tier === "local" ? "Local forensic" : tier.charAt(0).toUpperCase() + tier.slice(1)}
        </Button>
      ))}
    </div>
  );
}

function SectionsGrid({ model }: { model: ForensicModel }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ForensicSectionCard
        title="USER INPUT"
        status={model.userInput.status}
        testId="section-user-input"
      >
        <ForensicSectionCard.Json value={model.userInput.data} />
      </ForensicSectionCard>

      <ForensicSectionCard
        title="TURN CONTRACT"
        status={model.turnContract.status}
        testId="section-turn-contract"
      >
        <ForensicSectionCard.Json value={model.turnContract.data} />
      </ForensicSectionCard>

      <ForensicSectionCard title="EVIDENCE" status={model.evidence.status} testId="section-evidence">
        <ForensicSectionCard.Json value={model.evidence.data} />
      </ForensicSectionCard>

      <ForensicSectionCard
        title="NOT DISCLOSED"
        status={model.notDisclosed.status}
        testId="section-not-disclosed"
      >
        <ForensicSectionCard.Json value={model.notDisclosed.data} />
      </ForensicSectionCard>

      <ForensicSectionCard
        title="RELATIONAL BOOTSTRAP"
        status={model.relationalBootstrap.status}
        testId="section-relational-bootstrap"
      >
        <ForensicSectionCard.Json value={model.relationalBootstrap.data} />
      </ForensicSectionCard>

      <ForensicSectionCard title="HANDOFF" status={model.handoff.status} testId="section-handoff">
        <ForensicSectionCard.Json value={model.handoff.data} />
      </ForensicSectionCard>

      <ForensicSectionCard title="AGENT WORK" status={model.agentWork.status} testId="section-agent-work">
        <ForensicSectionCard.Json value={model.agentWork.data} />
      </ForensicSectionCard>

      <ForensicSectionCard title="AUTHORITY" status={model.authority.status} testId="section-authority">
        <ForensicSectionCard.Json value={model.authority.data} />
      </ForensicSectionCard>

      <ForensicSectionCard
        title="REMOTE PAYLOAD"
        status={model.remotePayload.status}
        testId="section-remote-payload"
      >
        <ForensicSectionCard.Json value={model.remotePayload.data} />
      </ForensicSectionCard>

      <ForensicSectionCard
        title="STREAMING TRACE"
        status={model.streamingTrace.status}
        testId="section-streaming-trace"
      >
        {model.streamingTrace.data ? (
          <pre
            className="mt-1 overflow-x-auto whitespace-pre font-mono text-sm"
            data-testid="streaming-trace-timeline"
          >
            {model.streamingTrace.data.formatted}
          </pre>
        ) : null}
      </ForensicSectionCard>

      <ForensicSectionCard title="MEMORY" status={model.memory.status} testId="section-memory">
        <ForensicSectionCard.Json value={model.memory.data} />
      </ForensicSectionCard>
    </div>
  );
}

export function V2DebugPanel() {
  const { world } = useWorld();
  const { attention, busy, loading, client, items: sessionItems } = useEnigmaConversation();
  const { activeThread } = useV2Threads();
  const { lastTrace, forensicTurn } = useStreamTrace();
  const items = activeThread.items.length > 0 ? activeThread.items : sessionItems;
  const [provenance, setProvenance] = useState<ProvenanceView | null>(null);
  const [snapshotCopied, setSnapshotCopied] = useState(false);

  const work = useMemo(
    () => workSnapshotFromConversation({ items, busy, loading }),
    [items, busy, loading],
  );

  useEffect(() => {
    const target = work.inspectTarget;
    if (!target) {
      setProvenance(null);
      return;
    }
    void client.getProvenance(target).then(setProvenance).catch(() => setProvenance(null));
  }, [client, work.inspectTarget]);

  const model = useMemo(
    () =>
      buildForensicModel({
        items,
        attention,
        busy,
        loading,
        world,
        provenance,
        streamingTrace: lastTrace,
        forensicTurn,
      }),
    [items, attention, busy, loading, world, provenance, lastTrace, forensicTurn],
  );

  const copySnapshot = useCallback(async () => {
    await copyTextToClipboard(JSON.stringify(model.snapshot, null, 2));
    setSnapshotCopied(true);
    window.setTimeout(() => setSnapshotCopied(false), 1500);
  }, [model.snapshot]);

  return (
    <div className="v2-root min-h-dvh" data-testid="v2-debug-panel">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs text-muted-foreground">Semantic Forensics · read-model only</p>
            <h1 className="text-xl font-semibold tracking-tight">Debug</h1>
          </div>
          <Link to="/v2" className="text-sm underline text-muted-foreground hover:text-foreground">
            Back to chat
          </Link>
        </header>

        <TurnSnapshotBar model={model} onCopySnapshot={() => void copySnapshot()} copied={snapshotCopied} />

        <Tabs defaultValue="sections">
          <TabsList>
            <TabsTrigger value="sections">Sections</TabsTrigger>
            <TabsTrigger value="copy">Copy bundles</TabsTrigger>
            <TabsTrigger value="why-not">Why not?</TabsTrigger>
          </TabsList>

          <TabsContent value="sections">
            <SectionsGrid model={model} />
          </TabsContent>

          <TabsContent value="copy">
            <div className="space-y-3 rounded-lg border border-border p-4">
              <p className="text-sm text-muted-foreground">
                Safe tier omits raw private fields. Local forensic stays on this machine until you share it.
              </p>
              <CopyBundles model={model} />
            </div>
          </TabsContent>

          <TabsContent value="why-not">
            <ForensicSectionCard
              title="Why not?"
              status={model.whyNot.status}
              description="can_wait_summary read-model — not a Turn Contract, not reconstructed intent."
              testId="section-why-not"
            >
              <ForensicSectionCard.Json value={model.whyNot.data} />
            </ForensicSectionCard>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
