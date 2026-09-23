# Generischer Gebäude-Renderer (Raumgeometrie)

## Rendering-Stack (Stand nach Three.js-Migration)

| Schicht | Technologie | Rolle |
|---------|-------------|--------|
| **Darstellung** | `three` + `@react-three/fiber` + `@react-three/drei` | WebGL, OrbitControls, Raycast-Klicks, `EdgesGeometry` |
| **Lösung / Prüfung** | `backend/app/core/iso_building.py` | `building_projections`, `score_derived_projection_answer`, `valid_cube_net`, `classify_column_visibility` — **ohne** Three.js |

Die frühere SVG/Handformel-Schicht (`isoBuilding.ts` Projektion) bleibt nur noch für **Klassifikation/Hinweise** (`classifyColumnVisibility`); Gebäudebilder laufen über `BuildingThreeCanvas` / `VoxelBuilding`.

**Voxel-Liste:** `listVoxelsFromHeightMatrix` rendert jeden Würfel mit Höhe > 0 (kein Iso-Culling — nötig für freies Drehen mit OrbitControls). Regression: `frontend/src/lib/voxelList.test.ts` (Vitest).

## Komponenten

- `frontend/src/components/learn/BuildingThreeCanvas.tsx`
- `frontend/src/components/learn/buildingThree/VoxelBuilding.tsx`
- `BuildingIsoPreview`, `RegionPaintExercise` (mit `height_matrix`), `GridFillExercise`, `SyntheticViewpointExercise`

Legacy `region_paint` **ohne** `height_matrix` nutzt weiterhin SVG-Polygone (alte Template-IDs).

## Backend / KI-Schema

Unverändert: `height_matrix`, `colored_faces` (`x,y,z,face`), `building_paint`, `derived_projection`, `net_build`, `synthetic_viewpoint`.

## Offen

- Quader-Netze (Flächengrössen)
- Strenger Normalen-BFS für `valid_cube_net`
- Optional: `InstancedMesh` für sehr grosse Matrizen (bei max. 8×8 derzeit nicht nötig)

## net_build

Bewertung akzeptiert jedes gültige Würfelnetz (`answer` in Practice immer `"valid_net"`). KI-Prompt verlangt ebenfalls nur `"valid_net"`.

## Deploy

Nach Pull: `cd frontend && npm install` (neue Pakete `three`, `@react-three/fiber`, `@react-three/drei`).
