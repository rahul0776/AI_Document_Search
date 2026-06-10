// frontend/src/lib/api.ts

const configuredApiBase = process.env.REACT_APP_API_BASE;
if (!configuredApiBase && process.env.NODE_ENV === "production") {
  // Fail loudly instead of silently pointing a production build at localhost.
  throw new Error("REACT_APP_API_BASE must be set at build time for production builds.");
}
export const API_BASE = configuredApiBase || "http://localhost:8000";

/* ───────────── Shared helpers ───────────── */
function getToken() {
  return localStorage.getItem("token") || "";
}

function withAuthHeaders(init?: RequestInit): Headers {
  const headers = new Headers(init?.headers as HeadersInit);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const t = getToken();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  return headers;
}

async function fetchJson(input: RequestInfo, init?: RequestInit) {
  const res = await fetch(input, {
    ...init,
    headers: withAuthHeaders(init),
  });

  if (res.status === 401) {
    localStorage.removeItem("token");
    throw new Error("Unauthorized. Please sign in.");
  }
  if (!res.ok) {
    let msg = "Request failed";
    try {
      const j = await res.json();
      msg = j.detail || j.message || msg;
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

/* ───────────── Auth ───────────── */
export async function signup(username: string, email: string, password: string) {
  return fetchJson(`${API_BASE}/auth/signup`, {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  }) as Promise<{ token: string; user: { user_id: string; email?: string } }>;
}

export async function login(username: string, password: string) {
  return fetchJson(`${API_BASE}/auth/login`, {
    method: "POST",
    body: JSON.stringify({ username, password }),
  }) as Promise<{ token: string; user: { user_id: string; email?: string } }>;
}

export async function getMe() {
  return fetchJson(`${API_BASE}/me`) as Promise<{ user_id: string; email?: string; email_verified?: boolean }>;
}

export async function verifyEmail(token: string) {
  return fetchJson(`${API_BASE}/auth/verify-email`, {
    method: "POST",
    body: JSON.stringify({ token }),
  }) as Promise<{ ok: boolean; message: string }>;
}

export async function resendVerification() {
  return fetchJson(`${API_BASE}/auth/resend-verification`, {
    method: "POST",
    body: JSON.stringify({}),
  }) as Promise<{ ok: boolean; message: string }>;
}

export async function forgotPassword(email: string) {
  return fetchJson(`${API_BASE}/auth/forgot-password`, {
    method: "POST",
    body: JSON.stringify({ email }),
  }) as Promise<{ ok: boolean; message: string }>;
}

export async function resetPassword(token: string, new_password: string) {
  return fetchJson(`${API_BASE}/auth/reset-password`, {
    method: "POST",
    body: JSON.stringify({ token, new_password }),
  }) as Promise<{ ok: boolean; message: string }>;
}

/* ───────────── Types ───────────── */
export type Retrieved = { text: string; page: number; doc_id: string; score: number };
export type Citation  = { doc_id: string; page: number; excerpt: string };
export type DocMeta   = { doc_id: string; filename: string; pages: number; uploaded_at?: string; title?: string };

/* ───────────── Upload ───────────── */
export async function uploadPdf(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: fd,
    headers: (() => {
      // Auth for multipart: don't set Content-Type manually
      const t = getToken();
      return t ? { Authorization: `Bearer ${t}` } : undefined;
    })(),
  });
  if (res.status === 401) {
    localStorage.removeItem("token");
    throw new Error("Unauthorized. Please sign in.");
  }
  if (!res.ok) throw new Error("Upload failed");
  return res.json() as Promise<{ doc_id: string; chunks: number }>;
}

/* ───────────── Ask / Chat ───────────── */
export async function ask(
  question: string,
  top_k = 5,
  docId?: string
): Promise<{ results: Retrieved[] }> {
  const body: any = { question, top_k };
  if (docId) body.doc_id = docId;
  return fetchJson(`${API_BASE}/ask`, { method: "POST", body: JSON.stringify(body) });
}

export async function chat(
  question: string,
  top_k = 5,
  docId?: string
): Promise<{ answer: string; citations: Citation[] }> {
  const body: any = { question, top_k };
  if (docId) body.doc_id = docId;
  return fetchJson(`${API_BASE}/chat`, { method: "POST", body: JSON.stringify(body) });
}

/**
 * Streaming chat (SSE over fetch).
 * We stream with fetch + ReadableStream instead of EventSource so the JWT can be
 * sent in the Authorization header — never as a query param that ends up in
 * proxy/access logs and browser history.
 */
export function chatStream(
  question: string,
  top_k: number,
  onToken: (t: string) => void,
  onDone: (payload: { citations: Citation[] }) => void,
  onError?: (e: any) => void,
  docId?: string
) {
  const url = new URL(`${API_BASE}/chat_stream`);
  url.searchParams.set("question", question);
  url.searchParams.set("top_k", String(top_k));
  if (docId) url.searchParams.set("doc_id", docId);

  const controller = new AbortController();
  let closed = false;

  (async () => {
    try {
      const headers: Record<string, string> = { Accept: "text/event-stream" };
      const t = getToken();
      if (t) headers.Authorization = `Bearer ${t}`;

      const res = await fetch(url.toString(), { headers, signal: controller.signal });
      if (!res.ok || !res.body) throw new Error(`Stream failed (${res.status})`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let eventName = "message";
      let dataLines: string[] = [];

      const dispatch = () => {
        if (dataLines.length === 0) {
          eventName = "message";
          return;
        }
        const data = dataLines.join("\n");
        const ev = eventName;
        dataLines = [];
        eventName = "message";
        if (ev === "token") {
          onToken(data);
        } else if (ev === "done") {
          closed = true;
          controller.abort();
          try {
            onDone(JSON.parse(data));
          } catch {
            onDone({ citations: [] });
          }
        }
        // "ping" heartbeats are ignored
      };

      // Minimal SSE parser: lines are "event: ..." / "data: ...", blank line dispatches.
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let nl: number;
        while ((nl = buf.indexOf("\n")) >= 0) {
          let line = buf.slice(0, nl);
          buf = buf.slice(nl + 1);
          if (line.endsWith("\r")) line = line.slice(0, -1);
          if (line === "") {
            dispatch();
          } else if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).replace(/^ /, ""));
          }
        }
      }
    } catch (e) {
      if (!closed) onError?.(e);
    }
  })();

  // Returned closer: user-initiated stop must not trigger onError.
  return () => {
    closed = true;
    controller.abort();
  };
}

/* ───────────── Docs ───────────── */
export async function listDocs() {
  return fetchJson(`${API_BASE}/documents`, { method: "GET" }) as Promise<{ docs: DocMeta[] }>;
}

export async function deleteDoc(docId: string) {
  return fetchJson(`${API_BASE}/documents/${docId}`, { method: "DELETE" }) as Promise<{ ok: boolean }>;
}
