import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";

type Props = {
  docId: string;
  page: number;
  onClose: () => void;
};

export default function PdfPanel({ docId, page, onClose }: Props) {
  const [numPages, setNumPages] = useState<number>(0);
  const [curr, setCurr] = useState<number>(page || 1);
  const containerRef = useRef<HTMLDivElement>(null);

  const fileUrl = `${process.env.REACT_APP_API_BASE || "http://localhost:8000"}/files/${docId}.pdf`;

  useEffect(() => setCurr(page || 1), [page]);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-stretch justify-end z-50">
      <div className="w-[min(900px,95vw)] bg-white h-full shadow-2xl flex flex-col">
        <div className="p-3 border-b flex items-center gap-2">
          <div className="font-medium">PDF Viewer</div>
          <div className="text-xs text-gray-500 ml-2">doc {docId.slice(0,8)}…</div>
          <div className="ml-auto flex items-center gap-2">
            <button
              className="px-2 py-1 text-sm rounded border"
              onClick={() => setCurr((p) => Math.max(1, p - 1))}
            >
              Prev
            </button>
            <span className="text-sm">p{curr}/{numPages || "?"}</span>
            <button
              className="px-2 py-1 text-sm rounded border"
              onClick={() => setCurr((p) => Math.min(numPages || p + 1, p + 1))}
              disabled={!numPages}
            >
              Next
            </button>
            <button className="px-3 py-1 rounded bg-black text-white" onClick={onClose}>
              Close
            </button>
          </div>
        </div>

        <div ref={containerRef} className="flex-1 overflow-auto px-4 py-3">
          <Document
            file={fileUrl}
            onLoadSuccess={({ numPages }) => setNumPages(numPages)}
            loading={<div className="p-4 text-sm">Loading PDF…</div>}
            error={<div className="p-4 text-sm text-red-600">Failed to load PDF</div>}
          >
            {/* Render all pages so scrolling is natural; auto-scroll to target page */}
            {Array.from(new Array(numPages || 0), (_, idx) => {
              const p = idx + 1;
              return (
                <div key={p} id={`pdf-page-${p}`} className="mb-4 flex justify-center">
                  <Page
                    pageNumber={p}
                    width={800}
                    renderAnnotationLayer={false}
                    renderTextLayer={false}
                    onRenderSuccess={() => {
                      if (p === curr) {
                        document.getElementById(`pdf-page-${p}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
                      }
                    }}
                  />
                </div>
              );
            })}
          </Document>
        </div>
      </div>
    </div>
  );
}
