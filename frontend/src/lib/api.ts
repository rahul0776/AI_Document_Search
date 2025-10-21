// frontend/src/lib/api.ts

export const API_BASE =
  process.env.REACT_APP_API_BASE || "http://localhost:8000";

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

/* ───────────── Auth (Day 13) ───────────── */
export async function devLogin(user_id: string, email?: string) {
  return fetchJson(`${API_BASE}/auth/dev_login`, {
    method: "POST",
    body: JSON.stringify({ user_id, email }),
  }) as Promise<{ token: string; user: { user_id: string; email?: string } }>;
}

export async function getMe() {
  return fetchJson(`${API_BASE}/me`) as Promise<{ user_id: string; email?: string }>;
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
 * Streaming chat (SSE).
 * EventSource can’t send headers; we append `token` as a query param.
 * Backend should accept either Header Bearer or ?token=… (Day 13 Option A).
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
  const t = getToken();
  if (t) url.searchParams.set("token", t); // << add token for SSE

  const es = new EventSource(url.toString());

  es.addEventListener("token", (ev: MessageEvent) => onToken(ev.data));
  es.addEventListener("done", (ev: MessageEvent) => {
    try {
      onDone(JSON.parse(ev.data));
    } catch {
      onDone({ citations: [] });
    } finally {
      es.close();
    }
  });
  es.onerror = (e) => {
    es.close();
    onError?.(e);
  };
  return () => es.close();
}

/* ───────────── Docs ───────────── */
export async function listDocs() {
  return fetchJson(`${API_BASE}/documents`, { method: "GET" }) as Promise<{ docs: DocMeta[] }>;
}

export async function deleteDoc(docId: string) {
  return fetchJson(`${API_BASE}/documents/${docId}`, { method: "DELETE" }) as Promise<{ ok: boolean }>;
}
