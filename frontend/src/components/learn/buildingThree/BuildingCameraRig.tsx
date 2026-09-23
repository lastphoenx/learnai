"use client";

import { useEffect } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import type { SpatialCameraPreset } from "@/lib/spatialCoordinates";
import type { HeightMatrix } from "@/lib/isoBuilding";
import { cameraPoseForPreset } from "@/lib/buildingCamera";

type Props = {
  matrix: HeightMatrix;
  preset: SpatialCameraPreset;
};

export function BuildingCameraRig({ matrix, preset }: Props) {
  const { camera } = useThree();

  useEffect(() => {
    const pose = cameraPoseForPreset(matrix, preset);
    camera.position.set(...pose.position);
    camera.zoom = pose.zoom;
    if (camera instanceof THREE.OrthographicCamera) {
      camera.updateProjectionMatrix();
    }
    camera.lookAt(new THREE.Vector3(...pose.target));
  }, [camera, matrix, preset]);

  return null;
}
