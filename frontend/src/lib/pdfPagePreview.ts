/** Client-seitige PDF-Vorschau für Batch-Wizard (lazy Thumbnails). */

let workerReady = false;

async function ensurePdfJs() {
  const pdfjs = await import("pdfjs-dist");
  if (!workerReady) {
    pdfjs.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
    workerReady = true;
  }
  return pdfjs;
}

export async function loadPdfDocument(file: File) {
  const pdfjs = await ensurePdfJs();
  const data = new Uint8Array(await file.arrayBuffer());
  return pdfjs.getDocument({ data }).promise;
}

export async function renderPdfPageThumbnail(
  doc: import("pdfjs-dist").PDFDocumentProxy,
  pageNum: number,
  maxWidth = 120,
): Promise<string> {
  const page = await doc.getPage(pageNum);
  const viewport = page.getViewport({ scale: 1 });
  const scale = maxWidth / viewport.width;
  const scaled = page.getViewport({ scale });
  const canvas = document.createElement("canvas");
  canvas.width = Math.floor(scaled.width);
  canvas.height = Math.floor(scaled.height);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas nicht verfügbar");
  await page.render({ canvasContext: ctx, viewport: scaled }).promise;
  return canvas.toDataURL("image/jpeg", 0.72);
}
