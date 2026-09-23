/**
 * Würfelnetz-Faltsimulation — muss mit backend `cube_net_cell_face_mapping` übereinstimmen.
 */

export type Vec3 = [number, number, number];

const NET_DIRS: [number, number][] = [[0, -1], [0, 1], [1, 0], [-1, 0]];

const FOLD_PALETTE = ["#3c76e8", "#e6c200", "#2d9f4e", "#8b4bb8", "#e07b2d", "#159b83"];

function cross(a: Vec3, b: Vec3): Vec3 {
  return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
}

function dot(a: Vec3, b: Vec3): number {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function add(a: Vec3, b: Vec3): Vec3 {
  return [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
}

function scale(a: Vec3, k: number): Vec3 {
  return [a[0] * k, a[1] * k, a[2] * k];
}

function rotate90(v: Vec3, axis: Vec3): Vec3 {
  return add(cross(axis, v), scale(axis, dot(axis, v)));
}

function normKey(v: Vec3): string {
  return `${v[0]},${v[1]},${v[2]}`;
}

function netCellsConnected(cells: [number, number][]): boolean {
  const cellSet = new Set(cells.map((c) => `${c[0]},${c[1]}`));
  if (cellSet.size !== cells.length) return false;
  const start = cells[0];
  const seen = new Set<string>([`${start[0]},${start[1]}`]);
  const queue: [number, number][] = [start];
  while (queue.length) {
    const [cx, cy] = queue.shift()!;
    for (const [dx, dy] of NET_DIRS) {
      const n: [number, number] = [cx + dx, cy + dy];
      const key = `${n[0]},${n[1]}`;
      if (cellSet.has(key) && !seen.has(key)) {
        seen.add(key);
        queue.push(n);
      }
    }
  }
  return seen.size === cells.length;
}

export function cubeNetCellFaceMapping(cells: [number, number][]): Map<string, Vec3> | null {
  if (cells.length !== 6) return null;
  if (!netCellsConnected(cells)) return null;
  const start = cells[0];
  const frames = new Map<string, [Vec3, Vec3, Vec3]>();
  frames.set(`${start[0]},${start[1]}`, [[0, 0, 1], [1, 0, 0], [0, 1, 0]]);
  const faceOf = new Map<string, Vec3>();
  faceOf.set(`${start[0]},${start[1]}`, [0, 0, 1]);
  const cellSet = new Set(cells.map((c) => `${c[0]},${c[1]}`));
  const seen = new Set<string>([`${start[0]},${start[1]}`]);
  const queue: [number, number][] = [start];
  while (queue.length) {
    const [cx, cy] = queue.shift()!;
    const frame = frames.get(`${cx},${cy}`)!;
    const [normal, ex, ey] = frame;
    for (const [dx, dy] of NET_DIRS) {
      const n: [number, number] = [cx + dx, cy + dy];
      const key = `${n[0]},${n[1]}`;
      if (!cellSet.has(key) || seen.has(key)) continue;
      const travel = add(scale(ex, dx), scale(ey, dy));
      const axis = cross(normal, travel);
      const newNormal = rotate90(normal, axis);
      frames.set(key, [newNormal, rotate90(ex, axis), rotate90(ey, axis)]);
      faceOf.set(key, newNormal);
      seen.add(key);
      queue.push(n);
    }
  }
  if (seen.size !== 6) return null;
  const uniqueNormals = new Set(faceOf.values().map(normKey));
  if (uniqueNormals.size !== 6) return null;
  return faceOf;
}

export function validCubeNet(cells: [number, number][]): boolean {
  return cubeNetCellFaceMapping(cells) !== null;
}

/** Farben/Labels F1–F6 pro Rasterzelle (key `col,row`). */
export function cubeNetFoldLabels(cells: [number, number][]): Record<string, { label: string; color: string }> | null {
  const mapping = cubeNetCellFaceMapping(cells);
  if (!mapping) return null;
  const normals = [...new Set([...mapping.values()].map(normKey))].sort();
  const labelOf = new Map(normals.map((k, i) => [k, { label: `F${i + 1}`, color: FOLD_PALETTE[i % FOLD_PALETTE.length] }]));
  const out: Record<string, { label: string; color: string }> = {};
  for (const [cellKey, normal] of mapping.entries()) {
    const meta = labelOf.get(normKey(normal));
    if (meta) out[cellKey] = meta;
  }
  return out;
}
