import type { EgressDisclosure } from "./types";

export const DISCLOSURE_RECENT_PATH = "/private/disclosure/recent";

export class DisclosureUnavailableError extends Error {
  readonly status: number;
  readonly endpoint: string;
  readonly expected = "application/json";
  readonly received: string;
  readonly correlationId: string;
  readonly preview?: string;

  constructor(init: {
    status: number;
    endpoint?: string;
    received: string;
    correlationId: string;
    preview?: string;
  }) {
    super("Privacy disclosure unavailable");
    this.name = "DisclosureUnavailableError";
    this.status = init.status;
    this.endpoint = init.endpoint ?? DISCLOSURE_RECENT_PATH;
    this.received = init.received;
    this.correlationId = init.correlationId;
    this.preview = init.preview;
  }
}

function looksLikeHtml(text: string): boolean {
  const trimmed = text.trimStart().toLowerCase();
  return trimmed.startsWith("<!doctype") || trimmed.startsWith("<html");
}

function receivedType(contentType: string, text: string): string {
  const mime = contentType.split(";")[0]?.trim();
  if (mime) {
    return mime;
  }
  if (looksLikeHtml(text)) {
    return "text/html";
  }
  return "unknown";
}

function htmlPreview(text: string): string | undefined {
  if (!looksLikeHtml(text)) {
    return undefined;
  }
  return text.trimStart().slice(0, 80);
}

export function newDisclosureCorrelationId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `disc-fetch-${Date.now()}`;
}

export function disclosureErrorFromUnknown(
  err: unknown,
  correlationId = "n/a",
): DisclosureUnavailableError {
  if (err instanceof DisclosureUnavailableError) {
    return err;
  }
  const message = err instanceof Error ? err.message : "";
  const htmlParse = /unexpected token/i.test(message) || /<!doctype/i.test(message);
  return new DisclosureUnavailableError({
    status: htmlParse ? 200 : 0,
    received: htmlParse ? "text/html" : "unknown",
    correlationId,
  });
}

export async function readDisclosureList(
  response: Response,
  options: {
    endpoint?: string;
    correlationId: string;
    includePreview?: boolean;
  },
): Promise<EgressDisclosure[]> {
  const text = await response.text();
  const contentType = response.headers.get("content-type") ?? "";
  const received = receivedType(contentType, text);
  const includePreview = options.includePreview ?? Boolean(import.meta.env.DEV);
  const preview = includePreview ? htmlPreview(text) : undefined;

  const fail = (receivedOverride?: string): never => {
    throw new DisclosureUnavailableError({
      status: response.status,
      endpoint: options.endpoint,
      received: receivedOverride ?? received,
      correlationId: options.correlationId,
      preview,
    });
  };

  if (received.includes("html") || looksLikeHtml(text)) {
    fail("text/html");
  }

  let parsed: unknown;
  try {
    parsed = text.trim() ? JSON.parse(text) : {};
  } catch {
    fail(received === "unknown" ? "not JSON" : received);
  }

  if (!response.ok) {
    fail();
  }

  const disclosures =
    parsed && typeof parsed === "object" && "disclosures" in parsed
      ? (parsed as { disclosures: unknown }).disclosures
      : undefined;
  return Array.isArray(disclosures) ? (disclosures as EgressDisclosure[]) : [];
}
