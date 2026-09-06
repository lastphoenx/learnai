"use client";

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
  const src = `${sourceFileUrl(unitId, source.id)}?pack=1`;

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
