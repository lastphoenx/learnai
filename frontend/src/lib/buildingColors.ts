const COLOR_MAP: Record<string, string> = {
  yellow: "#e6c200",
  green: "#2d9f4e",
  purple: "#8b4bb8",
  blue: "#3b82c4",
  orange: "#e07b2d",
};

export function paletteColor(name: string | undefined, fallback = "#e2e8f0"): string {
  if (!name) return fallback;
  return COLOR_MAP[name] ?? name;
}
