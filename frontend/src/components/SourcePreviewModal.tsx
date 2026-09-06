"use client";

import { useEffect, useState } from "react";
import { HtmlPackFrame, isHtmlSource } from "@/components/HtmlPackFrame";
import { sourceFileUrl, type UnitSource } from "@/lib/api";

type Props = {
  unitId: string;
  source: UnitSource;
  onClose: () => void;
};

export function SourcePreviewModal({ unitId, source, onClose }: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const isImage = source.kind === "image" || (source.content_type || "").startsWith("image/");
  const isPdf = source.kind === "pdf" || source.kind === "document" || (source.content_type || "").includes("pdf");
  const isHtml = isHtmlSource(source);
  const name = source.original_name || "Quelle";

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    if (!source.has_file) return;
    const fileUrl = sourceFileUrl(unitId, source.id);
    if (isImage || isPdf || isHtml) {
      setUrl(fileUrl);
      return;
    }
    let cancelled = false;
    fetch(fileUrl, { credentials: "include" })
      .then((res) => {
        if (!res.ok) throw new Error("Datei nicht verfügbar");
        return res.blob();
      })
      .then((blob) => {
        if (!cancelled) setUrl(URL.createObjectURL(blob));
      })
      .catch(() => {
        if (!cancelled) setUrl(null);
      });
    return () => {
      cancelled = true;
    };
  }, [unitId, source.id, source.has_file, isImage, isPdf, isHtml]);

  useEffect(() => {
    return () => {
      if (url && url.startsWith("blob:")) URL.revokeObjectURL(url);
    };
  }, [url]);

  return (
    <div className="source-preview-backdrop" role="presentation" onClick={onClose}>
      <div
        className="source-preview-dialog card"
        role="dialog"
        aria-modal="true"
        aria-label={name}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="source-preview-head">
          <strong>{name}</strong>
          <button type="button" className="btn-sm ghost" onClick={onClose}>
            Schließen
          </button>
        </div>
        {!source.has_file ? (
          <p className="muted">Datei wurde entfernt — nur extrahierter Text bleibt erhalten.</p>
        ) : isImage && url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img className="source-preview-image" src={url} alt={name} />
        ) : isHtml && source.has_file ? (
          <HtmlPackFrame unitId={unitId} source={source} className="source-preview-frame html-pack-frame" />
        ) : isPdf && url ? (
          <iframe className="source-preview-frame" src={url} title={name} />
        ) : url ? (
          <p className="muted">
            Vorschau für diesen Dateityp nicht verfügbar.{" "}
            <a href={url} target="_blank" rel="noreferrer">
              Datei öffnen
            </a>
          </p>
        ) : (
          <p className="muted">Vorschau wird geladen…</p>
        )}
        {source.has_file && (
          <div className="source-preview-foot">
            {isHtml ? (
              <a className="btn-sm" href={`/units/${unitId}/pack/${source.id}`}>
                Vollbild öffnen
              </a>
            ) : (
              <a className="btn-sm" href={sourceFileUrl(unitId, source.id)} target="_blank" rel="noreferrer">
                In neuem Tab öffnen
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
