"use client";

import { useMemo, useRef } from "react";
import { OrbitControls } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import type { HeightMatrix } from "@/lib/isoBuilding";
import type { SpatialCameraPreset } from "@/lib/spatialCoordinates";
import { cameraPoseForPreset } from "@/lib/buildingCamera";
import * as THREE from "three";

type Props = {
  matrix: HeightMatrix;
  preset: SpatialCameraPreset;
  cameraLocked: boolean;
};

export function BuildingOrbitControls({ matrix, preset, cameraLocked }: Props) {
  const pose = useMemo(() => cameraPoseForPreset(matrix, preset), [matrix, preset]);
  const ref = useRef<OrbitControlsImpl>(null);
  const target = useMemo(() => new THREE.Vector3(...pose.target), [pose.target]);

  useFrame(() => {
    const controls = ref.current;
    if (!controls) return;
    controls.target.lerp(target, 0.35);
    controls.update();
  });

  return (
    <OrbitControls
      ref={ref}
      makeDefault
      target={pose.target}
      enableDamping
      dampingFactor={0.08}
      enableRotate={!cameraLocked}
      enablePan={!cameraLocked}
      enableZoom={!cameraLocked}
    />
  );
}
