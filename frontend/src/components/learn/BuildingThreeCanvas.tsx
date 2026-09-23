"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import type { HeightMatrix } from "@/lib/isoBuilding";
import { VoxelBuilding } from "@/components/learn/buildingThree/VoxelBuilding";
import { BuildingOrientationLabels } from "@/components/learn/buildingThree/BuildingOrientationLabels";
import { ViewpointSceneMarkers } from "@/components/learn/buildingThree/ViewpointSceneMarkers";
import type { ViewpointCandidateLike } from "@/lib/viewpointWorld";

export type BuildingThreeCanvasProps = {
  matrix: HeightMatrix;
  faceColors?: Record<string, string>;
  interactive?: boolean;
  onFaceClick?: (faceId: string) => void;
  slotCorrect?: Map<string, boolean>;
  heightPx?: number;
  showOrientationLabels?: boolean;
  viewpointCandidates?: ViewpointCandidateLike[];
  selectedViewpointId?: string | null;
  onViewpointPick?: (id: string) => void;
  viewpointPickDisabled?: boolean;
};

export function BuildingThreeCanvas({
  matrix,
  faceColors,
  interactive = false,
  onFaceClick,
  slotCorrect,
  heightPx = 300,
  showOrientationLabels = false,
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
        <ambientLight intensity={0.75} />
        <directionalLight position={[12, 18, 10]} intensity={0.95} />
        <Suspense fallback={null}>
          <VoxelBuilding
            matrix={matrix}
            faceColors={faceColors}
            interactive={interactive}
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
        <OrbitControls makeDefault enableDamping dampingFactor={0.08} />
      </Canvas>
    </div>
  );
}
