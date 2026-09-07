"use client";

import { useEffect, useState } from "react";
import { sourceFileUrl, type UnitSource } from "@/lib/api";

type Props = {
  unitId: string;
  source: UnitSource;
  title?: string;
  className?: string;
};

/** Sandboxed iframe for self-contained HTML exercise packs (ChatGPT etc.). */
export function HtmlPackFrame({ unitId, source, title, className }: Props) {
  const name = title || source.original_name || "HTML-Übung";
  const fileUrl = `${sourceFileUrl(unitId, source.id)}?pack=1`;
  const [src, setSrc] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(fileUrl, { credentials: "include" });
        if (!res.ok) {
          const msg =
            res.status === 401
              ? "Nicht angemeldet — Seite neu laden und erneut anmelden."
              : `HTML-Übung konnte nicht geladen werden (HTTP ${res.status}).`;
          throw new Error(msg);
        }
        const blob = await res.blob();
        if (cancelled) return;
        objectUrl = URL.createObjectURL(new Blob([blob], { type: "text/html; charset=utf-8" }));
        setSrc(objectUrl);
        setLoadError(null);
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : "Laden fehlgeschlagen");
          setSrc(null);
        }
      }
    })();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [fileUrl]);

  if (loadError) {
    return <p className="error">{loadError}</p>;
  }
  if (!src) {
    return <p className="muted">Lade HTML-Übung…</p>;
  }

  return (
    <iframe
      className={className || "html-pack-frame"}
      src={src}
      title={name}
      sandbox="allow-scripts allow-same-origin allow-forms"
      referrerPolicy="same-origin"
      allow=""
    />
  );
}

export function isHtmlSource(source: Pick<UnitSource, "kind" | "content_type">): boolean {
  return source.kind === "html" || (source.content_type || "").includes("html");
}
