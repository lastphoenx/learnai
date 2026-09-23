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

Legacy `region_paint` **ohne** `height_matrix` nutzt weiterhin SVG-Polygone (alte Template-IDs `iso_single_cube`, `iso_tower_2`). Die Pipeline setzt für diese Templates `height_matrix` bewusst auf `null`, damit Aufgabenstellung und Bewertung mit Flächen-IDs `top`/`left`/`right` übereinstimmen (kein Three.js-Raycast mit `0,0,0,top`).

## posten_compact + Raumgeometrie

**Kompakt** = weniger Karten/Quiz im JSON (z. B. 10/6 statt 12/8), **nicht** weniger Aufgabentypen oder leichtere Raumaufgaben. Spatial-Listen (`building_paint`, `net_build`, …) sind Pflicht (min. 2 Einträge); Fallback: `building_paint` + `net_build`.

- `grid_fill` + `derived_projection`: `reference_height_matrix` bzw. `height_matrix` im answer für die Gebäude-Vorschau.
- Einzelwürfel färben: `building_paint` mit `[[1]]`, nicht `region_paint`/`iso_single_cube`.
- `net_build` **validate**: `given_cells` + answer `valid`/`invalid`; Quader-Netze → `image_choice`.
- `synthetic_viewpoint`: Kandidaten mit `label` + Plan-`x`/`y`; UI: Grundriss-Kompass + **3D-👁-Marker** (`ViewpointSceneMarkers`) und Richtungslabels am Gebäude.

## Backend / KI-Schema

Unverändert: `height_matrix`, `colored_faces` (`x,y,z,face`), `building_paint`, `derived_projection`, `net_build`, `synthetic_viewpoint`.

## Offen

- Quader-Netze (Flächengrössen) — noch keine Kantenlängen im Datenmodell
- Optional: `InstancedMesh` für sehr grosse Matrizen (bei max. 8×8 derzeit nicht nötig)

## net_build

**Bauen:** Freitext-Formulierungen im KI-`prompt` werden beim Parsen verworfen — entweder generischer Text («beliebiges gültiges Netz») oder `target_cells` (6 Koordinaten) mit automatisch erzeugtem Aufgabentext und exakter Zell-Lösung. So entstehen keine Widersprüche wie «zweite Fläche» bei dritter Position.

**Prüfen:** `given_cells` + `valid`/`invalid`.

Ohne `target_cells` akzeptiert die Bewertung jedes gültige Würfelnetz (`answer` = `"valid_net"`). Mit `target_cells` muss die Markierung exakt diesen sechs Feldern entsprechen.

`valid_cube_net()` prüft nicht mehr nur Zusammenhang + Grad-Heuristik, sondern
faltet die 6 Zellen per Normalen-Simulation tatsächlich zu einem Würfel
(Drehung um die gemeinsame Kante, Kollisionsprüfung auf den 6 Flächen-Normalen).
Exhaustiv gegen alle 216 Sechszellen-Formen verifiziert: erkennt exakt die
11 bekannten Würfelnetz-Formen, lehnt u. a. den klassischen 2×3-Block
(Lehrbuch-Fangfrage) korrekt ab — die frühere Grad-Heuristik akzeptierte
diesen und weitere 14 Formen fälschlich. Regression: `test_valid_cube_net_*`
in `backend/tests/test_iso_building.py`.

## Deploy

Nach Pull: `cd frontend && npm install` (neue Pakete `three`, `@react-three/fiber`, `@react-three/drei`).
