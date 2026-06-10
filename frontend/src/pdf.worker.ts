// pdf.worker.ts
import { pdfjs } from "react-pdf";
// Bundle the worker locally — pdfjs-dist 5.x ships .mjs (the old cdnjs
// pdf.worker.min.js URL 404s), and bundling avoids a third-party CDN dependency.
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();
