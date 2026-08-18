import type { EnigmaEventHandler } from "./events";
import type {
  AssistProposal,
  AssistResult,
  AttentionState,
  ConversationItem,
  ConversationTurn,
  EgressDisclosure,
  ProvenanceView,
  QualificationDebug,
} from "./types";

export type Unsubscribe = () => void;

export interface EnigmaClient {
  getConversation(): Promise<ConversationItem[]>;
  sendMessage(text: string): Promise<ConversationTurn>;
  getAttentionState(): Promise<AttentionState>;
  getQualificationDebug(itemId: string): Promise<QualificationDebug>;
  getProvenance(itemId: string): Promise<ProvenanceView>;
  proposeAssist(intent: string): Promise<AssistProposal>;
  approveAssist(proposalId: string): Promise<AssistResult>;
  jumpCheckpoint(checkpointId: string): Promise<void>;
  listCheckpoints(): Promise<{ id: string; at: string; label: string }[]>;
  getDemoEvents(): Promise<import("./types").DemoEvent[]>;
  getRecentDisclosures(limit?: number): Promise<EgressDisclosure[]>;
  subscribe(handler: EnigmaEventHandler): Unsubscribe;
  isDemo(): boolean;
}
