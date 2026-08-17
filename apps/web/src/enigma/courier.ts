import type { CourierState, EvidenceBundle, GooseState, SourceName } from "./types";

const SOURCE_LABELS: Record<SourceName, string> = {
  calendar: "calendar",
  attention: "attention",
  next_actions: "next actions",
  world_changes: "recent changes",
  world_blockers: "blockers",
  sources_email: "email",
  sources_chat: "messages",
  weather: "weather",
  news: "live news",
  general_knowledge: "general knowledge",
};

export function formatSourceList(sources: SourceName[]): string {
  if (sources.length === 0) {
    return "";
  }
  const labels = sources.map((source) => SOURCE_LABELS[source] ?? source);
  if (labels.length === 1) {
    return labels[0]!;
  }
  if (labels.length === 2) {
    return `${labels[0]} and ${labels[1]}`;
  }
  return `${labels.slice(0, -1).join(", ")}, and ${labels[labels.length - 1]}`;
}

export function deriveCourierState(bundle: EvidenceBundle): CourierState {
  return bundle.courier_state;
}

export function deriveGooseState(bundle: EvidenceBundle): GooseState {
  switch (bundle.courier_state) {
    case "fetching":
      return bundle.unavailable_sources.length > 0 ? "waiting" : "searching";
    case "returned":
      return bundle.coverage_adequate ? "pleased" : "presenting";
    case "empty_pawed":
      return "empty_beaked";
    case "partially_returned":
      return bundle.evidence.length > 0 ? "huffing" : "returning";
    case "confused":
      return "presenting";
    case "blocked":
      return "waiting";
    default:
      return "idle";
  }
}

export function courierLine(bundle: EvidenceBundle, state: CourierState = bundle.courier_state): string {
  const searched = formatSourceList(bundle.searched_sources);
  const unsearched = formatSourceList(bundle.unsearched_sources);
  const unavailable = formatSourceList(bundle.unavailable_sources);

  switch (state) {
    case "fetching":
      return searched ? `THE Goose is checking ${searched}…` : "THE Goose is out looking.";
    case "returned":
      if (bundle.evidence.length > 0) {
        const count = bundle.evidence.reduce((sum, row) => sum + row.evidence_ids.length, 0);
        return `THE Goose came back with ${count} evidence ${count === 1 ? "item" : "items"}.`;
      }
      return searched ? `THE Goose checked ${searched}.` : "THE Goose came back with something useful.";
    case "empty_pawed":
      return searched
        ? `THE Goose checked ${searched} and came back empty-beaked.`
        : "THE Goose came back empty-beaked.";
    case "partially_returned": {
      const parts: string[] = ["THE Goose came back terribly pleased with itself."];
      if (searched) {
        parts.push(`I checked ${searched}`);
      }
      if (unsearched) {
        parts.push(`but didn't check ${unsearched}`);
      }
      if (unavailable) {
        parts.push(`and this session can't reach ${unavailable}`);
      }
      parts.push("— useful, but not enough to conclude the question is settled.");
      return parts.join(", ").replace(", —", " —");
    }
    case "confused": {
      const ref = bundle.unresolved_referents[0] ?? "that";
      return `THE Goose couldn't tell which ${ref} you meant yet.`;
    }
    case "blocked":
      if (bundle.unavailable_sources.includes("news")) {
        return "THE Goose can't reach live news from here.";
      }
      if (bundle.unavailable_sources.includes("weather")) {
        return "THE Goose can't reach weather from here.";
      }
      return "THE Goose found a locked door — that capability isn't available.";
    default:
      return "";
  }
}

export function courierStateClass(state: CourierState): string {
  return `evidence-courier--${state.replace("_", "-")}`;
}
