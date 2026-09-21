"use client";

type Bbox = { x: number; y: number; w: number; h: number };

type Props = {
  url: string;
  bbox: Bbox;
  alt?: string;
  className?: string;
};

/** Zeigt einen Ausschnitt eines Quellbilds (normierte bbox 0–1). */
export function SourceImageCrop({ url, bbox, alt = "", className = "" }: Props) {
  const w = Math.max(0.05, bbox.w);
  const h = Math.max(0.05, bbox.h);
  const imgWidthPct = 100 / w;
  const imgHeightPct = 100 / h;
  const leftPct = (-bbox.x / w) * 100;
  const topPct = (-bbox.y / h) * 100;

  return (
    <div
      className={`source-image-crop ${className}`.trim()}
      style={{ position: "relative", overflow: "hidden", aspectRatio: `${w} / ${h}` }}
    >
      <img
        src={url}
        alt={alt}
        draggable={false}
        style={{
          position: "absolute",
          width: `${imgWidthPct}%`,
          height: `${imgHeightPct}%`,
          left: `${leftPct}%`,
          top: `${topPct}%`,
          maxWidth: "none",
        }}
      />
    </div>
  );
}
