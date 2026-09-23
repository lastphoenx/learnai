"use client";

type Props = {
  palette: string[];
  colorMap: Record<string, string>;
  selectedColor: string;
  onSelect: (color: string) => void;
  disabled?: boolean;
};

export function RegionPaintPalette({ palette, colorMap, selectedColor, onSelect, disabled }: Props) {
  return (
    <div className="region-paint-palette" role="toolbar" aria-label="Farben">
      {palette.map((c) => (
        <button
          key={c}
          type="button"
          className={`region-paint-swatch${selectedColor === c ? " active" : ""}`}
          style={{ background: colorMap[c] || c }}
          disabled={disabled}
          aria-label={c}
          onClick={() => onSelect(c)}
        />
      ))}
    </div>
  );
}
