"use client";

import { Html } from "@react-three/drei";
import type { HeightMatrix } from "@/lib/isoBuilding";
import {
  type ViewpointCandidateLike,
  buildingGroupOffset,
  planNormToLocalPosition,
  resolveViewpointNorm,
} from "@/lib/viewpointWorld";

type Props = {
  matrix: HeightMatrix;
  candidates: ViewpointCandidateLike[];
  selectedId?: string | null;
  disabled?: boolean;
  onPick: (id: string) => void;
};

function Marker({
  position,
  id,
  label,
  selected,
  disabled,
  onPick,
}: {
  position: [number, number, number];
  id: string;
  label: string;
  selected: boolean;
  disabled?: boolean;
  onPick: (id: string) => void;
}) {
  const color = selected ? "#159b83" : "#3c76e8";
  return (
    <group position={position}>
      <mesh
        onClick={(e) => {
          if (disabled) return;
          e.stopPropagation();
          onPick(id);
        }}
        onPointerOver={(e) => {
          if (!disabled) e.stopPropagation();
        }}
      >
        <sphereGeometry args={[0.26, 20, 20]} />
        <meshStandardMaterial color={color} emissive={selected ? "#0c705e" : "#2456bb"} emissiveIntensity={0.35} />
      </mesh>
      <Html center distanceFactor={10} style={{ pointerEvents: "none" }}>
        <div
          style={{
            background: color,
            color: "#fff",
            fontWeight: 800,
            fontSize: "0.72rem",
            padding: "4px 8px",
            borderRadius: 10,
            border: "2px solid #fff",
            boxShadow: "0 2px 8px rgba(16,38,63,0.25)",
            maxWidth: 140,
            textAlign: "center",
            lineHeight: 1.2,
          }}
        >
          <div>👁 {id}</div>
          <div style={{ fontWeight: 600, fontSize: "0.65rem", marginTop: 2 }}>{label}</div>
        </div>
      </Html>
    </group>
  );
}

export function ViewpointSceneMarkers({ matrix, candidates, selectedId, disabled, onPick }: Props) {
  const cols = matrix[0]?.length ?? 1;
  const rows = matrix.length;
  const [ox, oy, oz] = buildingGroupOffset(matrix);

  return (
    <group position={[ox, oy, oz]}>
      {candidates.map((c) => {
        const [nx, ny] = resolveViewpointNorm(c);
        const pos = planNormToLocalPosition(nx, ny, cols, rows);
        const label = (c.label || "").trim() || `Standpunkt ${c.id}`;
        return (
          <Marker
            key={c.id}
            position={pos}
            id={c.id}
            label={label}
            selected={selectedId === c.id}
            disabled={disabled}
            onPick={onPick}
          />
        );
      })}
    </group>
  );
}
