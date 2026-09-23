/** Isometrischer Gebäude-Renderer (Höhenmatrix → SVG). */

export type HeightMatrix = number[][];

export type IsoCamera = "default" | "back";

export type RegionPaintRegion = {
  id: string;
  label?: string;
  points: [number, number][];
};

const ISO_ORIGIN_X = 210;
const ISO_ORIGIN_Y = 250;
const ISO_DX = 38;
const ISO_DY = 19;
const ISO_DZ = 38;

export function isoPoint(x: number, y: number, z: number, camera: IsoCamera = "default"): [number, number] {
  let gx = x;
  let gy = y;
  if (camera === "back") {
    gx = -x;
    gy = -y;
  }
  return [ISO_ORIGIN_X + (gx - gy) * ISO_DX, ISO_ORIGIN_Y + (gx + gy) * ISO_DY - z * ISO_DZ];
}

function heightAt(matrix: HeightMatrix, x: number, y: number): number {
  if (y < 0 || y >= matrix.length || x < 0 || x >= matrix[0].length) return 0;
  return matrix[y][x] ?? 0;
}

function facePolygon(
  x: number,
  y: number,
  z: number,
  face: "top" | "left" | "right",
  camera: IsoCamera,
): [number, number][] {
  if (face === "top") {
    return [
      isoPoint(x, y, z + 1, camera),
      isoPoint(x + 1, y, z + 1, camera),
      isoPoint(x + 1, y + 1, z + 1, camera),
      isoPoint(x, y + 1, z + 1, camera),
    ];
  }
  if (face === "left") {
    return [
      isoPoint(x, y, z + 1, camera),
      isoPoint(x, y + 1, z + 1, camera),
      isoPoint(x, y + 1, z, camera),
      isoPoint(x, y, z, camera),
    ];
  }
  return [
    isoPoint(x + 1, y, z + 1, camera),
    isoPoint(x + 1, y + 1, z + 1, camera),
    isoPoint(x, y + 1, z + 1, camera),
    isoPoint(x, y, z + 1, camera),
  ];
}

function faceVisible(matrix: HeightMatrix, x: number, y: number, z: number, face: "top" | "left" | "right"): boolean {
  if (face === "top") return z + 1 >= heightAt(matrix, x, y);
  if (face === "left") return z >= heightAt(matrix, x - 1, y);
  return z >= heightAt(matrix, x, y - 1);
}

export function faceId(x: number, y: number, z: number, face: string): string {
  return `${x},${y},${z},${face}`;
}

type FaceEntry = { x: number; y: number; z: number; face: "top" | "left" | "right"; depth: number };

function iterDrawFaces(matrix: HeightMatrix, camera: IsoCamera): FaceEntry[] {
  const rows = matrix.length;
  const cols = matrix[0]?.length ?? 0;
  const out: FaceEntry[] = [];
  const yRange = camera === "back" ? Array.from({ length: rows }, (_, i) => i) : Array.from({ length: rows }, (_, i) => rows - 1 - i);
  for (const y of yRange) {
    const xRange =
      camera === "back"
        ? Array.from({ length: cols }, (_, i) => cols - 1 - i)
        : Array.from({ length: cols }, (_, i) => i);
    for (const x of xRange) {
      const h = heightAt(matrix, x, y);
      for (let z = 0; z < h; z++) {
        for (const face of ["top", "left", "right"] as const) {
          if (!faceVisible(matrix, x, y, z, face)) continue;
          const depth = camera === "back" ? -(x + y) : x + y;
          out.push({ x, y, z, face, depth });
        }
      }
    }
  }
  out.sort((a, b) => a.depth - b.depth);
  return out;
}

export type ColumnVisibility = {
  col: number;
  readable: boolean;
  maxHeight: number;
  criticalDepthY: number;
  label: string;
};

export function classifyColumnVisibility(matrix: HeightMatrix): {
  allReadable: boolean;
  columns: ColumnVisibility[];
} {
  const cols = matrix[0]?.length ?? 0;
  const visible = new Set(
    iterDrawFaces(matrix, "default").map((f) => faceId(f.x, f.y, f.z, f.face)),
  );
  const columns: ColumnVisibility[] = [];
  for (let col = 0; col < cols; col++) {
    const heights = matrix.map((row) => row[col] ?? 0);
    const maxHeight = Math.max(...heights, 0);
    let criticalDepthY = heights.findIndex((h) => h === maxHeight);
    if (criticalDepthY < 0) criticalDepthY = 0;
    const zTop = Math.max(0, maxHeight - 1);
    const readable =
      maxHeight < 1 ||
      ["top", "left", "right"].some((face) => visible.has(faceId(col, criticalDepthY, zTop, face)));
    const letter = String.fromCharCode(65 + col);
    columns.push({
      col,
      readable,
      maxHeight,
      criticalDepthY,
      label: letter,
    });
  }
  return { allReadable: columns.every((c) => c.readable), columns };
}

export type ColumnInspectorResult = {
  col: number;
  colLabel: string;
  markers: {
    depth: number;
    x: number;
    y: number;
    height: number;
    isCritical: boolean;
  }[];
  guidePath: [number, number][];
  breakdown: string;
  maxHeight: number;
  criticalDepth: number;
};

export function buildColumnInspector(matrix: HeightMatrix, col: number, camera: IsoCamera = "default"): ColumnInspectorResult {
  const rows = matrix.length;
  const heights = matrix.map((row) => row[col] ?? 0);
  const maxHeight = Math.max(...heights, 0);
  let criticalDepthY = heights.findIndex((h) => h === maxHeight);
  if (criticalDepthY < 0) criticalDepthY = 0;
  const colLabel = String.fromCharCode(65 + col);
  const markers = heights.map((h, depthY) => {
    const z = h > 0 ? h : 0;
    const [px, py] = isoPoint(col, depthY, z, camera);
    return {
      depth: depthY + 1,
      x: px + 38,
      y: py - 8,
      height: h,
      isCritical: depthY === criticalDepthY && h === maxHeight,
    };
  });
  return {
    col,
    colLabel,
    markers,
    guidePath: markers.map((m) => [m.x, m.y] as [number, number]),
    breakdown: heights.map((h, i) => `Tiefe ${i + 1}=${h}`).join(" · "),
    maxHeight,
    criticalDepth: criticalDepthY + 1,
  };
}

export function buildRegionPaintLayout(
  matrix: HeightMatrix,
  options?: { viewWidth?: number; viewHeight?: number; title?: string; camera?: IsoCamera },
): {
  title: string;
  view_width: number;
  view_height: number;
  regions: RegionPaintRegion[];
  column_visibility?: ReturnType<typeof classifyColumnVisibility>;
} {
  const camera = options?.camera ?? "default";
  const viewWidth = options?.viewWidth ?? 400;
  const viewHeight = options?.viewHeight ?? 300;
  const padding = 24;
  const faces = iterDrawFaces(matrix, camera);
  const polys = faces.map((f) => facePolygon(f.x, f.y, f.z, f.face, camera));
  const xs = polys.flatMap((p) => p.map((pt) => pt[0]));
  const ys = polys.flatMap((p) => p.map((pt) => pt[1]));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = Math.max(maxX - minX, 1);
  const spanY = Math.max(maxY - minY, 1);
  const innerW = viewWidth - 2 * padding;
  const innerH = viewHeight - 2 * padding;
  const scale = Math.min(innerW / spanX, innerH / spanY);
  const regions: RegionPaintRegion[] = faces.map((f, i) => {
    const points = polys[i].map(([px, py]) => {
      const nx = (px - minX) * scale + padding;
      const ny = (py - minY) * scale + padding;
      return [nx / viewWidth, ny / viewHeight] as [number, number];
    });
    return { id: faceId(f.x, f.y, f.z, f.face), label: `${f.face} (${f.x},${f.y},${f.z})`, points };
  });
  return {
    title: options?.title ?? (camera === "back" ? "Gebäude (Rückansicht)" : "Gebäude (isometrisch)"),
    view_width: viewWidth,
    view_height: viewHeight,
    regions,
    column_visibility: classifyColumnVisibility(matrix),
  };
}

/** Flächen nur zum Anzeigen (Vorschau, nicht klickbar). */
export function buildIsoPreviewFaces(
  matrix: HeightMatrix,
  camera: IsoCamera = "default",
): { points: [number, number][]; fill: string }[] {
  const faces = iterDrawFaces(matrix, camera);
  const palette = ["#e2e8f0", "#cbd5e1", "#94a3b8"];
  return faces.map((f, i) => ({
    points: facePolygon(f.x, f.y, f.z, f.face, camera),
    fill: palette[i % palette.length],
  }));
}
