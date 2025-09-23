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
    <section className="p-6 bg-white rounded-xl shadow space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Documents</h2>
        <div className="text-sm flex items-center gap-3">
          <label className="inline-flex items-center gap-1">
            <input
              type="radio"
              name="scope"
              checked={scope === "this"}
              onChange={() => {
                // If there's no active doc yet but we have docs, pick the first.
                if (!activeDoc && docs[0]) onSelect(docs[0].doc_id);
                else if (activeDoc) onSelect(activeDoc);
              }}
            />
            <span>This PDF</span>
          </label>
          <label className="inline-flex items-center gap-1">
            <input
              type="radio"
              name="scope"
              checked={scope === "all"}
              onChange={() => onSelect(null)}
            />
            <span>All PDFs</span>
          </label>
        </div>
      </div>

      {loading && <p className="text-sm text-gray-500">Loading…</p>}
      {err && <p className="text-sm text-red-600">{err}</p>}

      <ul className="mt-2 divide-y">
        {docs.map((d) => {
          const isActive = activeDoc === d.doc_id;
          return (
            <li key={d.doc_id} className="py-2 flex items-center gap-3">
              <button
                className={`text-sm px-2 py-1 rounded border transition ${
                  isActive ? "bg-black text-white" : "bg-gray-50 hover:bg-gray-100"
                }`}
                onClick={() => onSelect(d.doc_id)}
                title={d.doc_id}
                aria-pressed={isActive}
              >
                {d.filename}
                <span className="text-xs text-gray-500"> · p{d.pages || 0}</span>
              </button>

              <span className="text-xs text-gray-400 truncate" title={d.doc_id}>
                {d.doc_id.slice(0, 8)}…
              </span>

              <button
                onClick={() => handleDelete(d.doc_id)}
                className="ml-auto text-xs px-2 py-1 rounded border hover:bg-red-50 text-red-600"
              >
                Delete
              </button>
            </li>
          );
        })}

        {!loading && docs.length === 0 && (
          <li className="py-2 text-sm text-gray-500">No documents uploaded yet.</li>
        )}
      </ul>
    </section>
  );
}
