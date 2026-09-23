/**
 * Höhenmatrix-Hilfen (Klassifikation, Face-IDs).
 * 3D-Darstellung: `BuildingThreeCanvas` (Three.js), nicht mehr SVG-iso().
 */

export type HeightMatrix = number[][];

export function faceId(x: number, y: number, z: number, face: string): string {
  return `${x},${y},${z},${face}`;
}

function heightAt(matrix: HeightMatrix, x: number, y: number): number {
  if (y < 0 || y >= matrix.length || x < 0 || x >= matrix[0].length) return 0;
  return matrix[y][x] ?? 0;
}

function faceVisible(matrix: HeightMatrix, x: number, y: number, z: number, face: "top" | "left" | "right"): boolean {
  if (face === "top") return z + 1 >= heightAt(matrix, x, y);
  if (face === "left") return z >= heightAt(matrix, x - 1, y);
  return z >= heightAt(matrix, x, y - 1);
}

type FaceEntry = { x: number; y: number; z: number; face: "top" | "left" | "right" };

/** Iso-Sichtbarkeit (2D-Renderer); für Spalten-Lesbarkeit in der UI. */
function iterIsoPaintFaces(matrix: HeightMatrix): FaceEntry[] {
  const rows = matrix.length;
  const cols = matrix[0]?.length ?? 0;
  const out: FaceEntry[] = [];
  for (let y = rows - 1; y >= 0; y--) {
    for (let x = 0; x < cols; x++) {
      const h = heightAt(matrix, x, y);
      for (let z = 0; z < h; z++) {
        for (const face of ["top", "left", "right"] as const) {
          if (faceVisible(matrix, x, y, z, face)) {
            out.push({ x, y, z, face });
          }
        }
      }
    }
  }
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
  const visible = new Set(iterIsoPaintFaces(matrix).map((f) => faceId(f.x, f.y, f.z, f.face)));
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
