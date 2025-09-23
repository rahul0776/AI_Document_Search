import React, { useEffect, useRef, useState } from "react";
import { uploadPdf, ask, chat, chatStream } from "./lib/api";
import DocLibrary from "./components/DocLibrary";
import Toast from "./components/Toast";
import PdfPanel from "./components/PdfPanel";

type Retrieved = {
  text: string;
  page: number;
  doc_id: string;
  score: number;
};

type Citation = { doc_id: string; page: number; excerpt: string };

function Chip({
  children,
  title,
}: {
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <span
      title={title}
      className="text-xs bg-gray-100 border rounded px-2 py-1 whitespace-nowrap"
    >
      {children}
    </span>
  );
}

export default function App() {
  const [docId, setDocId] = useState<string>("");
  // NEW: query scope (null = all PDFs, string = only this doc)
  const [docListRefreshKey, setDocListRefreshKey] = useState(0);
  const [queryScopeDoc, setQueryScopeDoc] = useState<string | null>(null);

  const [question, setQuestion] = useState("");
  const [retrieved, setRetrieved] = useState<Retrieved[]>([]);
  const [answer, setAnswer] = useState<string>(""); // non-streaming RAG
  const [cites, setCites] = useState<Citation[]>([]); // non-streaming citations

  // streaming state
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [streamCites, setStreamCites] = useState<Citation[]>([]);
  const closeStreamRef = useRef<null | (() => void)>(null);

  // UI state
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  // PDF side panel
  const [showPdf, setShowPdf] =
    useState<{ docId: string; page: number } | null>(null);

  // stop streaming if component unmounts
  useEffect(() => {
    return () => {
      closeStreamRef.current?.();
    };
  }, []);

  async function handleUpload(file: File) {
    setError("");
    setNotice("");
    setRetrieved([]);
    setAnswer("");
    setCites([]);
    setStreamText("");
    setStreamCites([]);
    setStreaming(false);
    setBusy(true);
    try {
      const r = await uploadPdf(file);
      setDocId(r.doc_id);
      // NEW: set newly uploaded doc as the active query scope
      setQueryScopeDoc(r.doc_id);
      setDocListRefreshKey((k) => k + 1);
      setNotice(
        "Uploaded. Indexing in background — wait a few seconds before your first query."
      );
    } catch (e: any) {
      setError(e?.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleAsk() {
    setError("");
    setNotice("");
    setAnswer("");
    setCites([]);
    setStreamText("");
    setStreamCites([]);
    setStreaming(false);
    if (!question.trim()) return;
    setBusy(true);
    try {
      // NEW: pass queryScopeDoc (null = all PDFs, string = only that doc)
      const r = await ask(question, 5, queryScopeDoc || undefined);
      setRetrieved(r.results || []);
      if (!r.results?.length) {
        setNotice(
          "No results yet. If you just uploaded, wait a few seconds and try again."
        );
      }
    } catch (e: any) {
      setError(e?.message || "Search failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleChat() {
    setError("");
    setNotice("");
    if (!question.trim()) return;
    setBusy(true);
    try {
      // NEW: pass queryScopeDoc
      const r = await chat(question, 5, queryScopeDoc || undefined);
      setAnswer(r.answer);
      setCites(r.citations || []);
    } catch (e: any) {
      setError(e?.message || "Chat failed");
    } finally {
      setBusy(false);
    }
  }

  function handleChatStream() {
    setError("");
    setNotice("");
    if (!question.trim()) return;

    // reset + start streaming
    setStreaming(true);
    setStreamText("");
    setStreamCites([]);

    // NEW: pass queryScopeDoc into stream
    closeStreamRef.current = chatStream(
      question,
      5,
      (t) => setStreamText((prev) => prev + t),
      (payload) => {
        setStreamCites(payload.citations || []);
        setStreaming(false);
      },
      () => {
        setError("Streaming error");
        setStreaming(false);
      },
      queryScopeDoc || undefined
    );
  }

  function stopStream() {
    closeStreamRef.current?.();
    setStreaming(false);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Global toasts */}
      {error && (
        <Toast text={error} tone="error" onClose={() => setError("")} />
      )}
      {notice && (
        <Toast text={notice} tone="success" onClose={() => setNotice("")} />
      )}

      <header className="px-6 py-4 border-b bg-white">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <h1 className="text-2xl font-bold">AI Document Search (RAG)</h1>
          {docId && <Chip title={docId}>doc {docId.slice(0, 8)}…</Chip>}
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6 space-y-6">
        {/* NEW: Document Library + Scope toggle */}
        <DocLibrary
          activeDoc={docId}
          refreshKey={docListRefreshKey}
          onSelect={(chosen) => setQueryScopeDoc(chosen)} // null => all PDFs
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
              <span className="px-4 py-2 rounded-lg bg-black text-white">
                Choose File
              </span>
            </label>
            {busy && <Chip>Working…</Chip>}
          </div>
        </section>

        {/* Ask + RAG controls */}
        <section className="p-6 bg-white rounded-xl shadow space-y-4">
          <h2 className="text-xl font-semibold">Ask</h2>
          <div className="flex gap-2">
            <input
              className="flex-1 border rounded px-3 py-2"
              placeholder="Ask a question about your PDF(s)…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <button
              className="px-4 py-2 rounded bg-gray-800 text-white disabled:opacity-50"
              disabled={!question || busy || streaming}
              onClick={handleAsk}
            >
              Search
            </button>
            <button
              className="px-4 py-2 rounded bg-indigo-600 text-white disabled:opacity-50"
              disabled={!question || busy || streaming}
              onClick={handleChat}
            >
              Ask (RAG)
            </button>
            <button
              className="px-4 py-2 rounded bg-purple-600 text-white disabled:opacity-50"
              disabled={!question || busy || streaming}
              onClick={handleChatStream}
            >
              Ask (Stream)
            </button>
            {streaming && (
              <button
                className="px-3 py-2 rounded bg-gray-200 text-gray-800"
                onClick={stopStream}
              >
                Stop
              </button>
            )}
          </div>

          {/* Retrieval results */}
          {!!retrieved.length && (
            <ul className="space-y-2">
              {retrieved.map((a, i) => (
                <li key={i} className="p-3 rounded border bg-white">
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <Chip title={a.doc_id}>doc {a.doc_id.slice(0, 8)}…</Chip>
                    <Chip>page {a.page}</Chip>
                    <Chip>score {a.score.toFixed(3)}</Chip>
                  </div>
                  <div className="mt-2 text-sm leading-relaxed">{a.text}</div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Non-streaming answer */}
        {(answer || cites.length > 0) && (
          <section className="p-6 bg-white rounded-xl shadow space-y-3">
            <h2 className="text-xl font-semibold">Answer</h2>
            <div className="whitespace-pre-wrap">{answer}</div>
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

        {/* Streaming answer */}
        {(streamText || streamCites.length > 0 || streaming) && (
          <section className="p-6 bg-white rounded-xl shadow space-y-3">
            <h2 className="text-xl font-semibold">Answer (Streaming)</h2>
            <div className="whitespace-pre-wrap min-h-[3rem]">
              {streamText || (streaming ? "…" : "")}
            </div>
            {!!streamCites.length && (
              <div className="mt-2 flex flex-wrap gap-2">
                {streamCites.map((c, i) => (
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

        <p className="text-xs text-gray-500">
          Tip: After uploading a large PDF, wait a few seconds for background
          indexing before your first query.
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
