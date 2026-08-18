import type { DemoEvent } from "./types";

export type EnigmaEvent =
  | { type: "attention_changed"; checkpoint_id: string }
  | { type: "conversation_updated" }
  | { type: "demo_event"; event: DemoEvent }
  | { type: "status_changed" };

export type EnigmaEventHandler = (event: EnigmaEvent) => void;
