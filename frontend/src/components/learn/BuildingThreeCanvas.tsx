"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import type { HeightMatrix } from "@/lib/isoBuilding";
import { VoxelBuilding, type VoxelFaceInteraction } from "@/components/learn/buildingThree/VoxelBuilding";
import { BuildingOrientationLabels } from "@/components/learn/buildingThree/BuildingOrientationLabels";
import { ViewpointSceneMarkers } from "@/components/learn/buildingThree/ViewpointSceneMarkers";
import type { ViewpointCandidateLike } from "@/lib/viewpointWorld";
import type { SpatialCameraPreset } from "@/lib/spatialCoordinates";
import { BuildingCameraRig } from "@/components/learn/buildingThree/BuildingCameraRig";
import { BuildingOrbitControls } from "@/components/learn/buildingThree/BuildingOrbitControls";

export type BuildingThreeCanvasProps = {
  matrix: HeightMatrix;
  faceColors?: Record<string, string>;
  interactive?: boolean;
  faceInteraction?: VoxelFaceInteraction;
  onFaceClick?: (faceId: string) => void;
  slotCorrect?: Map<string, boolean>;
  heightPx?: number;
  showOrientationLabels?: boolean;
  /** Feste didaktische Kamera; Standard «oblique» (frühere Default-Ansicht). */
  cameraPreset?: SpatialCameraPreset;
  /** Kein Drehen/Zoomen (z. B. «reicht diese Sicht?»). */
  cameraLocked?: boolean;
  viewpointCandidates?: ViewpointCandidateLike[];
  selectedViewpointId?: string | null;
  onViewpointPick?: (id: string) => void;
  viewpointPickDisabled?: boolean;
};

export function BuildingThreeCanvas({
  matrix,
  faceColors,
  interactive = false,
  faceInteraction = "iso",
  onFaceClick,
  slotCorrect,
  heightPx = 300,
  showOrientationLabels = false,
  cameraPreset = "oblique",
  cameraLocked = false,
  viewpointCandidates,
  selectedViewpointId,
  onViewpointPick,
  viewpointPickDisabled = false,
}: BuildingThreeCanvasProps) {
  return (
    <div className="building-three-wrap" style={{ height: heightPx, maxWidth: "28rem", width: "100%" }}>
      <Canvas
        dpr={[1, 2]}
        camera={{ position: [7, 9, 7], zoom: 42, near: 0.1, far: 200 }}
        orthographic
        gl={{ antialias: true }}
      >
        <BuildingCameraRig matrix={matrix} preset={cameraPreset} />
        <ambientLight intensity={0.75} />
        <directionalLight position={[12, 18, 10]} intensity={0.95} />
        <Suspense fallback={null}>
          <VoxelBuilding
            matrix={matrix}
            faceColors={faceColors}
            interactive={interactive}
            faceInteraction={faceInteraction}
            onFaceClick={onFaceClick}
            slotCorrect={slotCorrect}
          />
          {showOrientationLabels && <BuildingOrientationLabels matrix={matrix} />}
          {viewpointCandidates && viewpointCandidates.length > 0 && onViewpointPick && (
            <ViewpointSceneMarkers
              matrix={matrix}
              candidates={viewpointCandidates}
              selectedId={selectedViewpointId}
              disabled={viewpointPickDisabled}
              onPick={onViewpointPick}
            />
          )}
        </Suspense>
        <BuildingOrbitControls matrix={matrix} preset={cameraPreset} cameraLocked={cameraLocked} />
      </Canvas>
    </div>
  );
}
