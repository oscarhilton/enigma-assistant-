/** Shared Core JSON reader — surface FastAPI `detail` instead of a raw status+URL. */

export async function readApiJson<T>(response: Response): Promise<T> {
  const url = response.url || "(unknown url)";
  const text = await response.text();
  if (!response.ok) {
    throw new Error(formatApiError(response.status, url, text));
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`API returned HTML / not JSON (${response.status}) ${url}`);
  }
}

export function formatApiError(status: number, url: string, body: string): string {
  const detail = parseFastApiDetail(body);
  if (status === 409 && detail) {
    if (/active world/i.test(detail)) {
      return `${detail} Switch the world switcher to match, then retry.`;
    }
    return detail;
  }
  if (detail) {
    return `${detail} (HTTP ${status})`;
  }
  return `HTTP ${status} ${url}`;
}

export function parseFastApiDetail(body: string): string | null {
  try {
    const parsed = JSON.parse(body) as { detail?: unknown };
    if (typeof parsed.detail === "string" && parsed.detail.trim()) {
      return parsed.detail.trim();
    }
  } catch {
    return null;
  }
  return null;
}
