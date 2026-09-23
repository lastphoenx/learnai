"use client";

import { useMemo, useRef } from "react";
import * as THREE from "three";
import { Edges } from "@react-three/drei";
import type { HeightMatrix } from "@/lib/isoBuilding";
import {
  BOX_MATERIAL_INDEX_TO_FACE,
  BUILDING_FACE_TO_MATERIAL,
  type BuildingFace,
  isExteriorBuildingFace,
} from "@/lib/cubeOrientation";
import { faceId } from "@/lib/isoBuilding";
import { paletteColor } from "@/lib/buildingColors";
import { listVoxelsFromHeightMatrix } from "@/lib/voxelList";

const BOX = 0.94;
const GAP = 1.02;

const ISO_FACES: BuildingFace[] = ["left", "top", "right"];

export type VoxelFaceInteraction = "iso" | "orientable";

type VoxelProps = {
  matrix: HeightMatrix;
  gx: number;
  gy: number;
  gz: number;
  faceColors: Record<string, string>;
  interactive: boolean;
  faceInteraction: VoxelFaceInteraction;
  onFaceClick?: (id: string) => void;
  slotCorrect?: Map<string, boolean>;
};

function Voxel({
  matrix,
  gx,
  gy,
  gz,
  faceColors,
  interactive,
  faceInteraction,
  onFaceClick,
  slotCorrect,
}: VoxelProps) {
  const meshRef = useRef<THREE.Mesh>(null);

  const materials = useMemo(() => {
    const mats = Array.from({ length: 6 }, () => new THREE.MeshStandardMaterial({ color: "#e2e8f0" }));
    const paintFaces = faceInteraction === "orientable" ? Object.keys(BUILDING_FACE_TO_MATERIAL) : ISO_FACES;
    for (const fname of paintFaces) {
      const midx = BUILDING_FACE_TO_MATERIAL[fname as BuildingFace];
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
  }, [gx, gy, gz, faceColors, slotCorrect, faceInteraction]);

  return (
    <mesh
      ref={meshRef}
      position={[gx * GAP, gz * GAP + BOX / 2, gy * GAP]}
      material={materials}
      onClick={(e) => {
        if (!interactive || !onFaceClick) return;
        e.stopPropagation();
        const idx = Math.floor((e.faceIndex ?? 0) / 2);
        const fname = BOX_MATERIAL_INDEX_TO_FACE[idx];
        if (!fname) return;
        if (faceInteraction === "iso" && !ISO_FACES.includes(fname)) return;
        if (!isExteriorBuildingFace(matrix, gx, gy, gz, fname)) return;
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
  faceInteraction?: VoxelFaceInteraction;
  onFaceClick?: (faceId: string) => void;
  slotCorrect?: Map<string, boolean>;
};

export function VoxelBuilding({
  matrix,
  faceColors = {},
  interactive = false,
  faceInteraction = "iso",
  onFaceClick,
  slotCorrect,
}: VoxelBuildingProps) {
  const voxels = useMemo(() => listVoxelsFromHeightMatrix(matrix), [matrix]);

  const cols = matrix[0]?.length ?? 1;
  const rows = matrix.length;
  const offsetX = -((cols - 1) * GAP) / 2;
  const offsetZ = -((rows - 1) * GAP) / 2;

  return (
    <group position={[offsetX, 0, offsetZ]}>
      {voxels.map((v) => (
        <Voxel
          key={`${v.gx},${v.gy},${v.gz}`}
          matrix={matrix}
          gx={v.gx}
          gy={v.gy}
          gz={v.gz}
          faceColors={faceColors}
          interactive={interactive}
          faceInteraction={faceInteraction}
          onFaceClick={onFaceClick}
          slotCorrect={slotCorrect}
        />
      ))}
    </group>
  );
}
