// frontend/src/components/DocLibrary.tsx
import { useEffect, useMemo, useState } from "react";
import { listDocs, deleteDoc } from "../lib/api";

type Doc = { doc_id: string; filename: string; pages: number; uploaded_at?: string };

export default function DocLibrary({
  activeDoc,
  onSelect,
  onDeleted,
  refreshKey,
}: {
  activeDoc?: string | null;                 // the currently “selected”/scoped doc (or null)
  onSelect: (docId: string | null) => void;  // choose doc for scope; null = All PDFs
  onDeleted?: (docId: string) => void;       // optional callback after deletion
  refreshKey?: number;                       // bump to force refresh from parent
}) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>("");

  // scope radio: “this” when a doc is selected, otherwise “all”
  const scope: "this" | "all" = useMemo(() => (activeDoc ? "this" : "all"), [activeDoc]);

  async function refresh() {
    try {
      setErr("");
      setLoading(true);
      const r = await listDocs();
      setDocs(r.docs || []);
    } catch (e: any) {
      setErr(e?.message || "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { refresh(); }, []);               // initial load
  useEffect(() => { if (refreshKey !== undefined) refresh(); }, [refreshKey]); // external refresh

  // If scope is “this” but there is no activeDoc yet and documents exist,
  // auto-select the first one so the UI isn’t stuck.
  useEffect(() => {
    if (!activeDoc && docs.length > 0 && scope === "this") {
      onSelect(docs[0].doc_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docs]);

  async function handleDelete(id: string) {
    try {
      await deleteDoc(id);
      onDeleted?.(id);

      // If we deleted the selected doc, switch to “All PDFs”
      if (activeDoc === id) onSelect(null);

      await refresh();

      // If nothing left, enforce All PDFs scope
      if (docs.length - 1 <= 0) onSelect(null);
    } catch (e: any) {
      setErr(e?.message || "Failed to delete document");
    }
  }

  return (
    <section className="p-6 bg-white dark:bg-gray-900 rounded-xl shadow border border-gray-200 dark:border-gray-700 space-y-4 transition-colors">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Documents</h2>
        <div className="text-sm flex items-center gap-3">
          <label className="inline-flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="scope"
              checked={scope === "this"}
              onChange={() => {
                // If there's no active doc yet but we have docs, pick the first.
                if (!activeDoc && docs[0]) onSelect(docs[0].doc_id);
                else if (activeDoc) onSelect(activeDoc);
              }}
              className="text-orange-600 focus:ring-orange-500"
            />
            <span className="text-gray-700 dark:text-gray-300">This PDF</span>
          </label>
          <label className="inline-flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="scope"
              checked={scope === "all"}
              onChange={() => onSelect(null)}
              className="text-orange-600 focus:ring-orange-500"
            />
            <span className="text-gray-700 dark:text-gray-300">All PDFs</span>
          </label>
        </div>
      </div>

      {loading && <p className="text-sm text-gray-500 dark:text-gray-400">Loading…</p>}
      {err && <p className="text-sm text-red-600">{err}</p>}

      <div className="grid grid-cols-1 gap-3">
        {docs.map((d) => {
          const isActive = activeDoc === d.doc_id;
          return (
            <div
              key={d.doc_id}
              className={`group relative flex items-center gap-4 p-4 rounded-lg border transition-all ${
                isActive
                  ? "bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20 border-orange-300 dark:border-orange-700 shadow-md"
                  : "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-orange-300 dark:hover:border-orange-700 hover:shadow-md"
              }`}
            >
              {/* PDF Icon */}
              <div className={`flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center ${
                isActive 
                  ? "bg-gradient-to-br from-yellow-500 to-orange-600" 
                  : "bg-gray-200 dark:bg-gray-700 group-hover:bg-gradient-to-br group-hover:from-yellow-500 group-hover:to-orange-600"
              } transition-all`}>
                <svg className={`w-7 h-7 ${isActive ? "text-white" : "text-gray-600 dark:text-gray-400 group-hover:text-white"} transition-colors`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>

              {/* Document Info */}
              <div className="flex-1 min-w-0" onClick={() => onSelect(d.doc_id)} role="button" tabIndex={0}>
                <h3 className="font-medium text-gray-900 dark:text-white truncate">
                  {d.filename}
                </h3>
                <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mt-1">
                  <span className="flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    {d.pages || 0} pages
                  </span>
                  {d.uploaded_at && (
                    <span className="flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {new Date(d.uploaded_at).toLocaleDateString()}
                    </span>
                  )}
                  <span className="text-xs text-gray-400 truncate flex-shrink-0" title={d.doc_id}>
                    ID: {d.doc_id.slice(0, 8)}…
                  </span>
                </div>
              </div>

              {/* Delete Button */}
              <button
                onClick={() => handleDelete(d.doc_id)}
                className="flex-shrink-0 p-2 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors"
                title="Delete document"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>

              {isActive && (
                <div className="absolute -top-1 -right-1 w-6 h-6 bg-gradient-to-br from-yellow-500 to-orange-600 rounded-full flex items-center justify-center">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              )}
            </div>
          );
        })}

        {!loading && docs.length === 0 && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">No documents uploaded yet.</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Upload a PDF to get started</p>
          </div>
        )}
      </div>
    </section>
  );
}
