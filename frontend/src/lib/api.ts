export const API_BASE =
  process.env.REACT_APP_API_BASE || "http://localhost:8000";

export async function uploadPdf(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: fd });
  if (!res.ok) throw new Error("Upload failed");
  return res.json() as Promise<{ doc_id: string; chunks: number }>;
}

export async function ask(question: string, top_k = 5) {
  const res = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k }),
  });
  if (!res.ok) throw new Error("Ask failed");
  return res.json() as Promise<{ results: Array<{text:string; page:number; doc_id:string; score:number}> }>;
}
export async function chat(question: string, top_k = 5) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k }),
  });
  if (!res.ok) throw new Error("Chat failed");
  return res.json() as Promise<{ answer: string; citations: Array<{doc_id:string; page:number; excerpt:string}> }>;
}

export function chatStream(
  question: string,
  top_k: number,
  onToken: (t: string) => void,
  onDone: (payload: { citations: Array<{ doc_id: string; page: number; excerpt: string }> }) => void,
  onError?: (e: any) => void
) {
  const url = `${API_BASE}/chat_stream?question=${encodeURIComponent(
    question
  )}&top_k=${top_k}`;

  const es = new EventSource(url);

  es.addEventListener("token", (ev: MessageEvent) => {
    onToken(ev.data);
  });

  es.addEventListener("done", (ev: MessageEvent) => {
    try {
      const payload = JSON.parse(ev.data);
      onDone(payload);
    } catch (e) {
      onDone({ citations: [] });
    } finally {
      es.close();
    }
  });

  es.onerror = (e) => {
    es.close();
    onError?.(e);
  };

  return () => es.close(); // return unsubscribe
}