"use client";

import { useMemo, useRef } from "react";
import * as THREE from "three";
import { Edges } from "@react-three/drei";
import type { HeightMatrix } from "@/lib/isoBuilding";
import { faceId } from "@/lib/isoBuilding";
import { paletteColor } from "@/lib/buildingColors";

const BOX = 0.94;
const GAP = 1.02;

/** BoxGeometry material index: 0 +X, 1 -X, 2 +Y, 3 -Y, 4 +Z, 5 -Z */
const FACE_TO_MATERIAL: Record<string, number> = {
  left: 1,
  top: 2,
  right: 5,
};

const MATERIAL_TO_FACE: Record<number, string> = {
  1: "left",
  2: "top",
  5: "right",
};

function heightAt(matrix: HeightMatrix, x: number, y: number): number {
  if (y < 0 || y >= matrix.length || x < 0 || x >= matrix[0].length) return 0;
  return matrix[y][x] ?? 0;
}

function faceVisible(matrix: HeightMatrix, x: number, y: number, z: number, face: string): boolean {
  if (face === "top") return z + 1 >= heightAt(matrix, x, y);
  if (face === "left") return z >= heightAt(matrix, x - 1, y);
  if (face === "right") return z >= heightAt(matrix, x, y - 1);
  return false;
}

type VoxelProps = {
  gx: number;
  gy: number;
  gz: number;
  faceColors: Record<string, string>;
  interactive: boolean;
  onFaceClick?: (id: string) => void;
  slotCorrect?: Map<string, boolean>;
};

function Voxel({ gx, gy, gz, faceColors, interactive, onFaceClick, slotCorrect }: VoxelProps) {
  const meshRef = useRef<THREE.Mesh>(null);

  const materials = useMemo(() => {
    const mats = Array.from({ length: 6 }, () => new THREE.MeshStandardMaterial({ color: "#e2e8f0" }));
    for (const [fname, midx] of Object.entries(FACE_TO_MATERIAL)) {
      const id = faceId(gx, gy, gz, fname);
      const painted = faceColors[id];
      if (painted) {
        mats[midx].color.set(paletteColor(painted));
      }
      const slot = slotCorrect?.get(id);
      if (slot === false) mats[midx].emissive.set("#fecaca");
      else if (slot === true) mats[midx].emissive.set("#bbf7d0");
    }
    return mats;
  }, [gx, gy, gz, faceColors, slotCorrect]);

  return (
    <mesh
      ref={meshRef}
      position={[gx * GAP, gz * GAP + BOX / 2, gy * GAP]}
      material={materials}
      onClick={(e) => {
        if (!interactive || !onFaceClick) return;
        e.stopPropagation();
        const idx = Math.floor((e.faceIndex ?? 0) / 2);
        const fname = MATERIAL_TO_FACE[idx];
        if (!fname) return;
        onFaceClick(faceId(gx, gy, gz, fname));
      }}
    >
      <boxGeometry args={[BOX, BOX, BOX]} />
      <Edges threshold={15} color="#2f4258" />
    </mesh>
  );
}

export type VoxelBuildingProps = {
  matrix: HeightMatrix;
  faceColors?: Record<string, string>;
  interactive?: boolean;
  onFaceClick?: (faceId: string) => void;
  slotCorrect?: Map<string, boolean>;
};

export function VoxelBuilding({
  matrix,
  faceColors = {},
  interactive = false,
  onFaceClick,
  slotCorrect,
}: VoxelBuildingProps) {
  const voxels = useMemo(() => {
    const out: { gx: number; gy: number; gz: number }[] = [];
    const rows = matrix.length;
    const cols = matrix[0]?.length ?? 0;
    for (let gy = 0; gy < rows; gy++) {
      for (let gx = 0; gx < cols; gx++) {
        const h = heightAt(matrix, gx, gy);
        for (let gz = 0; gz < h; gz++) {
          if (
            faceVisible(matrix, gx, gy, gz, "top") ||
            faceVisible(matrix, gx, gy, gz, "left") ||
            faceVisible(matrix, gx, gy, gz, "right")
          ) {
            out.push({ gx, gy, gz });
          }
        }
      }
    }
    return out;
  }, [matrix]);

  const cols = matrix[0]?.length ?? 1;
  const rows = matrix.length;
  const offsetX = -((cols - 1) * GAP) / 2;
  const offsetZ = -((rows - 1) * GAP) / 2;

  return (
    <group position={[offsetX, 0, offsetZ]}>
      {voxels.map((v) => (
        <Voxel
          key={`${v.gx},${v.gy},${v.gz}`}
          gx={v.gx}
          gy={v.gy}
          gz={v.gz}
          faceColors={faceColors}
          interactive={interactive}
          onFaceClick={onFaceClick}
          slotCorrect={slotCorrect}
        />
      ))}
    </group>
  );
}
