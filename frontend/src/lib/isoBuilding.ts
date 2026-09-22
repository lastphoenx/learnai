/** Isometrischer Gebäude-Renderer (Höhenmatrix → SVG-Flächen). */

const ISO_ORIGIN_X = 210;
const ISO_ORIGIN_Y = 250;
const ISO_DX = 38;
const ISO_DY = 19;
const ISO_DZ = 38;

export type HeightMatrix = number[][];

export type RegionPaintRegion = {
  id: string;
  label?: string;
  points: [number, number][];
};

export function isoPoint(x: number, y: number, z: number): [number, number] {
  return [ISO_ORIGIN_X + (x - y) * ISO_DX, ISO_ORIGIN_Y + (x + y) * ISO_DY - z * ISO_DZ];
}

function heightAt(matrix: HeightMatrix, x: number, y: number): number {
  if (y < 0 || y >= matrix.length || x < 0 || x >= matrix[0].length) return 0;
  return matrix[y][x] ?? 0;
}

function facePolygon(x: number, y: number, z: number, face: "top" | "left" | "right"): [number, number][] {
  if (face === "top") {
    return [isoPoint(x, y, z + 1), isoPoint(x + 1, y, z + 1), isoPoint(x + 1, y + 1, z + 1), isoPoint(x, y + 1, z + 1)];
  }
  if (face === "left") {
    return [isoPoint(x, y, z + 1), isoPoint(x, y + 1, z + 1), isoPoint(x, y + 1, z), isoPoint(x, y, z)];
  }
  return [isoPoint(x + 1, y, z + 1), isoPoint(x + 1, y + 1, z + 1), isoPoint(x, y + 1, z + 1), isoPoint(x, y, z + 1)];
}

function faceVisible(matrix: HeightMatrix, x: number, y: number, z: number, face: "top" | "left" | "right"): boolean {
  if (face === "top") return z + 1 >= heightAt(matrix, x, y);
  if (face === "left") return z >= heightAt(matrix, x - 1, y);
  return z >= heightAt(matrix, x, y - 1);
}

export function faceId(x: number, y: number, z: number, face: string): string {
  return `${x},${y},${z},${face}`;
}

export function buildRegionPaintLayout(
  matrix: HeightMatrix,
  options?: { viewWidth?: number; viewHeight?: number; title?: string }
): {
  title: string;
  view_width: number;
  view_height: number;
  regions: RegionPaintRegion[];
} {
  const viewWidth = options?.viewWidth ?? 400;
  const viewHeight = options?.viewHeight ?? 300;
  const padding = 24;
  const faces: { x: number; y: number; z: number; face: "top" | "left" | "right" }[] = [];
  const rows = matrix.length;
  const cols = matrix[0]?.length ?? 0;
  for (let y = rows - 1; y >= 0; y--) {
    for (let x = 0; x < cols; x++) {
      const h = heightAt(matrix, x, y);
      for (let z = 0; z < h; z++) {
        for (const face of ["top", "left", "right"] as const) {
          if (faceVisible(matrix, x, y, z, face)) faces.push({ x, y, z, face });
        }
      }
    }
  }
  const polys = faces.map((f) => facePolygon(f.x, f.y, f.z, f.face));
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
    title: options?.title ?? "Gebäude (isometrisch)",
    view_width: viewWidth,
    view_height: viewHeight,
    regions,
  };
}
