// src/lib/api.ts

export const API_BASE =
  process.env.REACT_APP_API_BASE || "http://localhost:8000";

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
  title?: string;          // <-- Day 8: optional title from backend
};

/* ───────────── Upload ───────────── */
export async function uploadPdf(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: fd });
  if (!res.ok) throw new Error("Upload failed");
  return res.json() as Promise<{ doc_id: string; chunks: number }>;
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Ask failed");
  return res.json();
}

/* ───────────── Docs: list & delete ───────────── */
export async function listDocs() {
  const res = await fetch(`${API_BASE}/documents`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error("Failed to list documents");
  return res.json() as Promise<{ docs: DocMeta[] }>;
}

export async function deleteDoc(docId: string) {
  const res = await fetch(`${API_BASE}/documents/${docId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete document");
  return res.json() as Promise<{ ok: boolean }>;
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Chat failed");
  return res.json();
}

/* ───────────── Chat (streaming SSE) ───────────── */
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
