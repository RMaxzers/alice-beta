import type { ChatRequest, ChatStreamEvent } from "./types";

let csrfToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

export function setUnauthorizedHandler(fn: (() => void) | null): void {
  unauthorizedHandler = fn;
}

export class ApiError extends Error {
  status: number;
  detail: string | null;
  constructor(status: number, message: string, detail: string | null) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function errorFromResponse(res: Response): Promise<ApiError> {
  let detail: string | null = null;
  try {
    const body = await res.json();
    if (body && typeof body.detail === "string") detail = body.detail;
    else if (body && typeof body.message === "string") detail = body.message;
  } catch {
    // no JSON body
  }
  return new ApiError(res.status, detail ?? `Error ${res.status}`, detail);
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (method !== "GET" && csrfToken) headers.set("x-csrf-token", csrfToken);
  const res = await fetch(path, { ...init, method, headers, credentials: "same-origin" });
  if (res.status === 401) unauthorizedHandler?.();
  return res;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await request(path);
  if (!res.ok) throw await errorFromResponse(res);
  return res.json() as Promise<T>;
}

export async function apiSend<T>(
  path: string,
  method: "POST" | "PUT" | "DELETE",
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {};
  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["content-type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await request(path, { method, headers, body: payload });
  if (!res.ok) throw await errorFromResponse(res);
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

/**
 * Streams a chat response as an async generator of parsed NDJSON events.
 * Consumers should iterate with `for await`.
 */
export async function* streamChat(
  body: ChatRequest,
  signal: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  const headers = new Headers({ "content-type": "application/json" });
  if (csrfToken) headers.set("x-csrf-token", csrfToken);
  const res = await fetch("/api/chat", {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    credentials: "same-origin",
    signal,
  });
  if (res.status === 401) {
    unauthorizedHandler?.();
    throw new ApiError(401, "No autorizado", null);
  }
  if (!res.ok || !res.body) {
    throw await errorFromResponse(res);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newlineIndex: number;
    while ((newlineIndex = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      if (line) yield JSON.parse(line) as ChatStreamEvent;
    }
  }
  const rest = buffer.trim();
  if (rest) yield JSON.parse(rest) as ChatStreamEvent;
}
