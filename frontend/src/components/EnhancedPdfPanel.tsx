// frontend/src/components/EnhancedPdfPanel.tsx
import React, { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface EnhancedPdfPanelProps {
  docId: string;
  initialPage?: number;
  onClose: () => void;
  highlightText?: string;
}

export default function EnhancedPdfPanel({ 
  docId, 
  initialPage = 1, 
  onClose,
  highlightText 
}: EnhancedPdfPanelProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState(initialPage);
  const [scale, setScale] = useState(1.0);
  const [showThumbnails, setShowThumbnails] = useState(false);
  const [loading, setLoading] = useState(true);

  const pdfUrl = `http://localhost:8000/pdf/${docId}`;

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
    setLoading(false);
  }

  const goToPage = (page: number) => {
    setPageNumber(Math.max(1, Math.min(page, numPages)));
  };

  const zoomIn = () => setScale(prev => Math.min(prev + 0.2, 3.0));
  const zoomOut = () => setScale(prev => Math.max(prev - 0.2, 0.5));
  const resetZoom = () => setScale(1.0);

  return (
    <div className="fixed inset-0 bg-black/50 dark:bg-black/70 z-50 flex">
      {/* Thumbnail sidebar */}
      {showThumbnails && numPages > 0 && (
        <div className="w-48 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 overflow-y-auto p-2">
          <div className="space-y-2">
            {Array.from({ length: numPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => goToPage(page)}
                className={`w-full p-2 rounded border-2 transition-all ${
                  page === pageNumber
                    ? 'border-orange-500 bg-orange-50 dark:bg-orange-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-orange-300 dark:hover:border-orange-700'
                }`}
              >
                <Document file={pdfUrl} loading="">
                  <Page
                    pageNumber={page}
                    width={150}
                    renderTextLayer={false}
                    renderAnnotationLayer={false}
                  />
                </Document>
                <p className="text-xs mt-1 text-gray-600 dark:text-gray-400">Page {page}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main PDF viewer */}
      <div className="flex-1 flex flex-col bg-gray-100 dark:bg-gray-800">
        {/* Toolbar */}
        <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 p-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Thumbnails toggle */}
            <button
              onClick={() => setShowThumbnails(!showThumbnails)}
              className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              title="Toggle thumbnails"
            >
              <svg className="w-5 h-5 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            {/* Page navigation */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => goToPage(pageNumber - 1)}
                disabled={pageNumber <= 1}
                className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 transition-colors"
              >
                <svg className="w-5 h-5 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              
              <span className="text-sm text-gray-700 dark:text-gray-300 min-w-[100px] text-center">
                {loading ? 'Loading...' : `Page ${pageNumber} of ${numPages}`}
              </span>
              
              <button
                onClick={() => goToPage(pageNumber + 1)}
                disabled={pageNumber >= numPages}
                className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 transition-colors"
              >
                <svg className="w-5 h-5 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>

            {/* Zoom controls */}
            <div className="flex items-center gap-2 border-l border-gray-200 dark:border-gray-700 pl-4">
              <button
                onClick={zoomOut}
                className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                title="Zoom out"
              >
                <svg className="w-5 h-5 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
                </svg>
              </button>
              
              <span className="text-sm text-gray-700 dark:text-gray-300 min-w-[60px] text-center">
                {Math.round(scale * 100)}%
              </span>
              
              <button
                onClick={zoomIn}
                className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                title="Zoom in"
              >
                <svg className="w-5 h-5 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                </svg>
              </button>
              
              <button
                onClick={resetZoom}
                className="text-xs px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 transition-colors"
                title="Reset zoom"
              >
                Reset
              </button>
            </div>
          </div>

          {/* Close button */}
          <button
            onClick={onClose}
            className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            title="Close"
          >
            <svg className="w-6 h-6 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* PDF content */}
        <div className="flex-1 overflow-auto p-8 flex justify-center">
          <div className="bg-white dark:bg-gray-700 shadow-2xl">
            <Document
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              loading={
                <div className="flex items-center justify-center p-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
                </div>
              }
              error={
                <div className="p-12 text-center text-red-600 dark:text-red-400">
                  <p>Failed to load PDF</p>
                </div>
              }
            >
              <Page
                pageNumber={pageNumber}
                scale={scale}
                renderTextLayer={true}
                renderAnnotationLayer={true}
              />
            </Document>
          </div>
        </div>

        {/* Keyboard shortcuts hint */}
        <div className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 px-4 py-2 text-xs text-gray-500 dark:text-gray-400 text-center">
          Keyboard: ← → (navigate) | + - (zoom) | Esc (close)
        </div>
      </div>
    </div>
  );
}

