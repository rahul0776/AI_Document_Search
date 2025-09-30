import React, { useEffect, useRef, useState } from "react";
import { uploadPdf, chat, chatStream, Citation } from "./lib/api";
import DocLibrary from "./components/DocLibrary";
import Toast from "./components/Toast";
import PdfPanel from "./components/PdfPanel";

/* ───────────── UI bits ───────────── */
function Chip({ children, title }: { children: React.ReactNode; title?: string }) {
  return (
    <span title={title} className="text-xs bg-gray-100 border rounded px-2 py-1 whitespace-nowrap">
      {children}
    </span>
  );
}
function copyToClipboard(text: string) {
  navigator.clipboard?.writeText(text).catch(() => {});
}
function downloadJSON(filename: string, obj: any) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/* ───────────── Types ───────────── */
type QAItem = {
  id: string;
  q: string;
  a: string;
  citations: Citation[];
  scopeLabel: string; // "All PDFs" or "This PDF"
  ts: number;
};

function scopeLabel(docId: string | null) {
  return docId ? "This PDF" : "All PDFs";
}

/* ───────────── App ───────────── */
export default function App() {
  // current “active” doc id (the one you just uploaded)
  const [docId, setDocId] = useState<string>("");

  // library + scope
  const [docListRefreshKey, setDocListRefreshKey] = useState(0);
  // null = query across all PDFs, string = restrict to that doc
  const [queryScopeDoc, setQueryScopeDoc] = useState<string | null>(null);

  // ask
  const [question, setQuestion] = useState("");

  // live answer (display box) – we still keep a separate history per request id
  const [answer, setAnswer] = useState<string>("");
  const [cites, setCites] = useState<Citation[]>([]);

  // conversation history (correctly paired Q/A, each with its own id)
  const [history, setHistory] = useState<QAItem[]>([]);

  // streaming control
  const [streaming, setStreaming] = useState(false);
  const closeStreamRef = useRef<null | (() => void)>(null);

  // UI state
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  // PDF side panel
  const [showPdf, setShowPdf] = useState<{ docId: string; page: number } | null>(null);

  useEffect(() => {
    return () => {
      // safety: close any open SSE on unmount
      closeStreamRef.current?.();
    };
  }, []);

  async function handleUpload(file: File) {
    setError(""); setNotice("");
    setAnswer(""); setCites([]);
    setStreaming(false);
    setBusy(true);
    try {
      const r = await uploadPdf(file);
      setDocId(r.doc_id);
      setQueryScopeDoc(r.doc_id);            // scope to this doc by default
      setDocListRefreshKey((k) => k + 1);    // refresh library
      setNotice("Uploaded. Indexing in background — wait a few seconds before your first query.");
    } catch (e: any) {
      setError(e?.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  /**
   * Single Ask button:
   * - Try streaming first and append tokens to a *request-scoped* history row.
   * - If streaming errors, gracefully fall back to non-streaming chat().
   */
  async function askSmart() {
    setError(""); setNotice("");
    if (!question.trim()) return;

    // Freeze values for this request
    const reqId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : String(Date.now());
    const q = question;                        // freeze question text
    const scope = scopeLabel(queryScopeDoc);   // freeze scope label

    // Create a draft history row immediately
    setHistory((h) => [
      ...h,
      { id: reqId, q, a: "", citations: [], scopeLabel: scope, ts: Date.now() },
    ]);

    // Reset live answer box (optional – history is the source of truth)
    setAnswer("");
    setCites([]);
    setStreaming(true);

    let finished = false;

    try {
      closeStreamRef.current = chatStream(
        q,
        5,
        // onToken: append to this row by id
        (t) => {
          setAnswer((prev) => (prev ? prev + t : t)); // live box
          setHistory((h) =>
            h.map((item) => (item.id === reqId ? { ...item, a: item.a + t } : item))
          );
        },
        // onDone: finalize citations for that row
        (payload) => {
          const c = payload.citations || [];
          setCites(c);
          setHistory((h) =>
            h.map((item) => (item.id === reqId ? { ...item, citations: c } : item))
          );
          finished = true;
          setStreaming(false);
        },
        // onError: graceful fallback to non-streaming
        async () => {
          closeStreamRef.current?.();
          setStreaming(false);
          if (!finished) {
            try {
              const r = await chat(q, 5, queryScopeDoc || undefined);
              setAnswer(r.answer);
              setCites(r.citations || []);
              setHistory((h) =>
                h.map((item) =>
                  item.id === reqId ? { ...item, a: r.answer, citations: r.citations || [] } : item
                )
              );
            } catch (e: any) {
              setError(e?.message || "Chat failed");
            }
          }
        },
        queryScopeDoc || undefined
      );
    } catch {
      // If EventSource creation fails (rare), non-stream fallback
      setStreaming(false);
      try {
        const r = await chat(q, 5, queryScopeDoc || undefined);
        setAnswer(r.answer);
        setCites(r.citations || []);
        setHistory((h) =>
          h.map((item) =>
            item.id === reqId ? { ...item, a: r.answer, citations: r.citations || [] } : item
          )
        );
      } catch (e: any) {
        setError(e?.message || "Chat failed");
      }
    }
  }

  function stopStream() {
    closeStreamRef.current?.();
    setStreaming(false);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Global toasts */}
      {error && <Toast text={error} tone="error" onClose={() => setError("")} />}
      {notice && <Toast text={notice} tone="success" onClose={() => setNotice("")} />}

      <header className="px-6 py-4 border-b bg-white">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <h1 className="text-2xl font-bold">AI Document Search (RAG)</h1>
          {docId && <Chip title={docId}>doc {docId.slice(0, 8)}…</Chip>}
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6 space-y-6">
        {/* Document library + scope */}
        <DocLibrary
          activeDoc={queryScopeDoc || ""}
          refreshKey={docListRefreshKey}
          onSelect={(chosen) => setQueryScopeDoc(chosen)}   // null => all PDFs
          onDeleted={(deletedId) => {
            if (docId === deletedId) setDocId("");
            if (queryScopeDoc === deletedId) setQueryScopeDoc(null);
          }}
        />

        {/* Upload */}
        <section className="p-6 bg-white rounded-xl shadow space-y-3">
          <h2 className="text-xl font-semibold">Upload PDF</h2>
          <div className="flex items-center gap-3">
            <label className="inline-flex items-center gap-2 cursor-pointer">
              <input
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleUpload(f);
                }}
              />
              <span className="px-4 py-2 rounded-lg bg-black text-white">Choose File</span>
            </label>
            {busy && <Chip>Working…</Chip>}
          </div>
        </section>

        {/* Ask (single button, streams with fallback) */}
        <section className="p-6 bg-white rounded-xl shadow space-y-4">
          <h2 className="text-xl font-semibold">Ask</h2>
          <div className="flex gap-2 items-center">
            <input
              className="flex-1 border rounded px-3 py-2"
              placeholder="Ask a question about your PDF(s)…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <button
              className="px-4 py-2 rounded bg-indigo-600 text-white disabled:opacity-50"
              disabled={!question || streaming}
              onClick={askSmart}
            >
              Ask
            </button>
            {streaming && (
              <button className="px-3 py-2 rounded bg-gray-200 text-gray-800" onClick={stopStream}>
                Stop
              </button>
            )}
          </div>
        </section>

        {/* Live Answer (also visible while streaming) */}
        {(answer || cites.length > 0 || streaming) && (
          <section className="p-6 bg-white rounded-xl shadow space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Answer</h2>
              <div className="flex gap-2">
                <button
                  className="text-xs px-2 py-1 rounded border hover:bg-gray-50"
                  onClick={() => copyToClipboard(answer)}
                  disabled={!answer}
                >
                  Copy answer
                </button>
                <button
                  className="text-xs px-2 py-1 rounded border hover:bg-gray-50"
                  onClick={() => downloadJSON("citations.json", cites)}
                  disabled={!cites.length}
                >
                  Export citations
                </button>
              </div>
            </div>

            <div className="whitespace-pre-wrap min-h-[3rem]">
              {answer || (streaming ? "…" : "")}
            </div>

            {!!cites.length && (
              <div className="mt-2 flex flex-wrap gap-2">
                {cites.map((c, i) => (
                  <button
                    key={i}
                    title={c.excerpt}
                    onClick={() => setShowPdf({ docId: c.doc_id, page: c.page })}
                    className="text-xs bg-gray-100 border rounded px-2 py-1 hover:bg-gray-200"
                  >
                    {c.doc_id.slice(0, 8)}… · p{c.page}
                  </button>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Previous answers (correctly paired, newest first) */}
        {history.length > 0 && (
          <section className="p-6 bg-white rounded-xl shadow space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Previous answers</h2>
              <div className="flex gap-2">
                <button
                  className="text-xs px-2 py-1 rounded border hover:bg-gray-50"
                  onClick={() =>
                    copyToClipboard(history.map((h) => `Q: ${h.q}\nA: ${h.a}`).join("\n\n"))
                  }
                >
                  Copy conversation
                </button>
                <button
                  className="text-xs px-2 py-1 rounded border hover:bg-gray-50"
                  onClick={() => downloadJSON("conversation.json", history)}
                >
                  Export conversation
                </button>
              </div>
            </div>

            {[...history].sort((a, b) => b.ts - a.ts).map((item) => (
              <div key={item.id} className="border rounded p-3 text-sm bg-white">
                <div className="text-gray-500 mb-1">
                  {new Date(item.ts).toLocaleString()} · {item.scopeLabel}
                </div>
                <div><strong>Q:</strong> {item.q}</div>
                <div className="mt-1"><strong>A:</strong> {item.a || "…"}</div>
              </div>
            ))}
          </section>
        )}

        <p className="text-xs text-gray-500">
          Tip: After uploading a large PDF, wait a few seconds for background indexing before your first query.
        </p>
      </main>

      {/* PDF side panel */}
      {showPdf && (
        <PdfPanel
          docId={showPdf.docId}
          page={showPdf.page}
          onClose={() => setShowPdf(null)}
        />
      )}
    </div>
  );
}
