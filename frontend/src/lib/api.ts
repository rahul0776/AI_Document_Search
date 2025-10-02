// src/lib/api.ts

export const API_BASE =
  process.env.REACT_APP_API_BASE || "http://localhost:8000";

/** Read auth token from localStorage (swap with Clerk/Auth0 later) */
function getToken(): string | null {
  return localStorage.getItem("token");
}

/** Common headers with optional Authorization */
function authHeaders(extra?: Record<string, string>) {
  const token = getToken();
  return {
    ...(extra || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

/* ───────────── Types ───────────── */
export type Retrieved = {
  text: string;
  page: number;
  doc_id: string;
  score: number;
};

export type Citation = {
  doc_id: string;
  page: number;
  excerpt: string;
};

export type DocMeta = {
  doc_id: string;
  filename: string;
  pages: number;
  uploaded_at?: string;
  title?: string; // Day 8+
};

/* ───────────── Helpers ───────────── */
export async function handleJson(res: Response) {
  if (!res.ok) {
    let msg = "Request failed";
    try {
      const j = await res.json();
      msg = j.message || j.detail || msg;
    } catch {
      // ignore parse errors
    }
    throw new Error(msg);
  }
  return res.json();
}

/* ───────────── Upload ───────────── */
export async function uploadPdf(file: File) {
  const fd = new FormData();
  fd.append("file", file);

  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    headers: authHeaders(), // include Authorization if present
    body: fd,
  });
  return handleJson(res) as Promise<{ doc_id: string; chunks: number }>;
}

/* ───────────── Ask (retrieve only) ───────────── */
export async function ask(
  question: string,
  top_k = 5,
  docId?: string
): Promise<{ results: Retrieved[] }> {
  const body: any = { question, top_k };
  if (docId) body.doc_id = docId;

  const res = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  return handleJson(res);
}

/* ───────────── Docs: list & delete ───────────── */
export async function listDocs() {
  const res = await fetch(`${API_BASE}/documents`, {
    headers: authHeaders({ Accept: "application/json" }),
  });
  return handleJson(res) as Promise<{ docs: DocMeta[] }>;
}

export async function deleteDoc(docId: string) {
  const res = await fetch(`${API_BASE}/documents/${docId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return handleJson(res) as Promise<{ ok: boolean }>;
}

/* ───────────── Chat (non-streaming) ───────────── */
export async function chat(
  question: string,
  top_k = 5,
  docId?: string
): Promise<{ answer: string; citations: Citation[] }> {
  const body: any = { question, top_k };
  if (docId) body.doc_id = docId;

  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  return handleJson(res);
}

/* ───────────── Chat (streaming SSE) ─────────────
   NOTE: EventSource cannot set custom headers. We pass the token
   as a query param so the backend can authenticate the stream. */
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

  // Day 11: attach token as query param for SSE auth
  const token = getToken();
  if (token) url.searchParams.set("token", token);

  const es = new EventSource(url.toString());

  es.addEventListener("token", (ev: MessageEvent) => {
    onToken(ev.data);
  });

  es.addEventListener("done", (ev: MessageEvent) => {
    try {
      const payload = JSON.parse(ev.data);
      onDone(payload);
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

  return () => es.close(); // unsubscribe/close
}
