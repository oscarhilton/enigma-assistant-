import {
  emptyWorkSnapshot,
  expressivenessFromRemoteContext,
  latestRemoteContext,
  licenseGoosePixels,
  type AgentWorkSnapshot,
  type GoosePixelLicence,
} from "../enigma/goosePixels";
import type { ConversationItem } from "../enigma/types";

/** AgentWork is the Goose source of truth while streaming — not prose deltas. */
export function workFromAgentWorkEvent(work: AgentWorkSnapshot | null): AgentWorkSnapshot {
  if (!work?.exists || work.phase === null) {
    return emptyWorkSnapshot();
  }
  return work;
}

export function gooseFromAgentWork(
  work: AgentWorkSnapshot | null,
  items: ConversationItem[] = [],
): GoosePixelLicence {
  return licenseGoosePixels(
    workFromAgentWorkEvent(work),
    expressivenessFromRemoteContext(latestRemoteContext(items)),
  );
}
