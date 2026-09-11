"use client";

import { useEffect, useRef, useState } from "react";
import { loadPdfDocument, renderPdfPageThumbnail } from "@/lib/pdfPagePreview";

type Props = {
  file: File;
  introFrom: number;
  introTo: number;
  activeRowIndex: number | null;
  rows: { pageFrom: number; pageTo: number }[];
  onPageClick: (page: number) => void;
};

export function BatchPdfPageGrid({
  file,
  introFrom,
  introTo,
  activeRowIndex,
  rows,
  onPageClick,
}: Props) {
  const [pageCount, setPageCount] = useState(0);
  const [thumbs, setThumbs] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const docRef = useRef<Awaited<ReturnType<typeof loadPdfDocument>> | null>(null);
  const gridRef = useRef<HTMLDivElement>(null);
  const pendingRef = useRef<Set<number>>(new Set());

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setThumbs({});
    setPageCount(0);
    docRef.current = null;
    pendingRef.current = new Set();

    void loadPdfDocument(file)
      .then((doc) => {
        if (cancelled) return;
        docRef.current = doc;
        setPageCount(doc.numPages);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "PDF konnte nicht gelesen werden");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      void docRef.current?.destroy();
      docRef.current = null;
    };
  }, [file]);

  useEffect(() => {
    const root = gridRef.current;
    if (!root || !pageCount) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const page = Number((entry.target as HTMLElement).dataset.page);
          if (!page || thumbs[page] || pendingRef.current.has(page) || !docRef.current) continue;
          pendingRef.current.add(page);
          void renderPdfPageThumbnail(docRef.current, page)
            .then((url) => {
              setThumbs((prev) => (prev[page] ? prev : { ...prev, [page]: url }));
            })
            .catch(() => undefined)
            .finally(() => {
              pendingRef.current.delete(page);
            });
        }
      },
      { root, rootMargin: "120px" },
    );
    root.querySelectorAll("[data-batch-page]").forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [pageCount, thumbs]);

  function pageClass(page: number) {
    const classes = ["batch-page-tile"];
    if (page >= introFrom && page <= introTo) classes.push("batch-page-intro");
    if (activeRowIndex != null) {
      const row = rows[activeRowIndex];
      if (row && page >= row.pageFrom && page <= row.pageTo) classes.push("batch-page-active-row");
    }
    for (let i = 0; i < rows.length; i += 1) {
      if (i === activeRowIndex) continue;
      const row = rows[i];
      if (row && page >= row.pageFrom && page <= row.pageTo) classes.push("batch-page-other-row");
    }
    return classes.join(" ");
  }

  if (loading) {
    return <p className="muted">PDF wird gelesen…</p>;
  }
  if (error) {
    return <p className="err">{error}</p>;
  }
  if (!pageCount) {
    return <p className="muted">Keine Seiten in der PDF.</p>;
  }

  return (
    <div className="batch-page-grid" role="list" aria-label="PDF-Seiten" ref={gridRef}>
      {Array.from({ length: pageCount }, (_, i) => i + 1).map((page) => (
        <button
          key={page}
          type="button"
          className={pageClass(page)}
          data-batch-page={page}
          data-page={page}
          onClick={() => onPageClick(page)}
          title={`Seite ${page}`}
        >
          {thumbs[page] ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={thumbs[page]} alt={`Seite ${page}`} loading="lazy" />
          ) : (
            <span className="batch-page-placeholder">S. {page}</span>
          )}
          <span className="batch-page-num">{page}</span>
        </button>
      ))}
    </div>
  );
}
