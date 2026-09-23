# Building Views Workshop (RaumWerkstatt Kap. 3)

Referenz-UX: `tempdok/RaumWerkstatt_Koerper_Ansichten_Plaene*.html`, Abschnitt **#views**.

## Komponenten (Frontend)

| Komponente | Rolle |
|------------|--------|
| `WorkshopShell` | Generisches Layout (workspace, aside, interaction, belowWorkspace, help) |
| `BuildingViewsWorkshopShell` | Kap. 3: Guide, Silhouetten-Text, Projektionsbereich |
| `BuildingWorkshopModelPanel` | Kontrolliert: `mode`, `unlockedModes`, `showColumnInspector` — Freischaltung durch `workshopModelUnlock.ts` |
| `BuildingObserverGuide` | «Wo steht der Betrachter?» |
| `VisibilityDecisionPanel` | Ja/Nein mit sofortigem Feedback (`expected_visibility`) |
| `SpatialSequenceExercise` | Kap. 3 — nutzt `useWorkshopFlow` + `spatialSequenceCapabilities` |
| `BuildingPlanWorkshopShell` | Kap. 4 Bauplan — Höhenplan statt Projektionen |
| `GridFillWorkshopExercise` | Kap. 4 bei `grid_fill.presentation: "workshop_v2"` + `derived_projection` |
| `BuildingStandpointWorkshopShell` | Kap. 6 Standort |
| `SyntheticViewpointWorkshopExercise` | Kap. 6 bei `synthetic_viewpoint.presentation: "workshop_v2"` |
| `BuildingPaintWorkshopShell` | Kap. 5 / Kap. 1 |
| `RegionPaintWorkshopExercise` | `building_paint.presentation: "workshop_v2"` + `height_matrix` |
| `ImageChoiceWorkshopExercise` | Kap. 1: `image_choice.presentation` + `orientation_cube` |
| `BuildingNetWorkshopShell` | Kap. 2 Netze |
| `NetBuildWorkshopExercise` | `net_build.presentation: "workshop_v2"` + `cubeNetFold.ts` |

Orientierungs-Kern (6 Flächen, stabil bei freier Kamera): `frontend/src/lib/cubeOrientation.ts` — `VoxelBuilding` `faceInteraction: "orientable"`.

Generische Freischaltung: `frontend/src/lib/workshop/` (`workshopCapabilities`, `useWorkshopFlow`).

## Backend

- `spatial_sequence.expected_visibility` — aus `compute_visibility_decision`, für UI-Feedback (nicht für End-Score allein).
- Antwort-JSON unverändert: `visibility` + `projections`.

## Schema (additiv)

- `grid_fill.presentation: "workshop_v2"` — Werkstatt-UI für Bauplan (`derived_projection` + `reference_height_matrix`).
- `synthetic_viewpoint.presentation: "workshop_v2"` — zweistufig: Schrägansicht, dann Standort-Wahl.
- `spatial_sequence` — unverändert; gleiches Capability-Muster wie bisher.
- `building_paint.presentation: "workshop_v2"` — drehen + Flächen tippen (`orientable`).
- `image_choice.presentation: "workshop_v2"` + `orientation_cube: { height_matrix, colored_faces }` — Würfel drehen, Bildoption wählen.
- `net_build.presentation: "workshop_v2"` — Faltvorschau (F1–F6).

Golden: `backend/app/fixtures/spatial_golden/nets.json`, `backend/tests/fixtures/posten_compact_raumwerkstatt.json`.

## Umfang RaumWerkstatt (workshop_v2)

| Kap. | answer_type | presentation + Voraussetzung |
|------|-------------|------------------------------|
| 1 | `image_choice` | + `orientation_cube` |
| 2 | `net_build` | Faltvorschau F1–F6 |
| 3 | `spatial_sequence` | (klassische Shell, Phasen-Fix) |
| 4 | `grid_fill` | + `derived_projection` + `reference_height_matrix` |
| 5 | `building_paint` | + `height_matrix` |
| 6 | `synthetic_viewpoint` | + `height_matrix` |

Kap. 3: `resolveSpatialSequenceWorkshopPhase` — bei fehlendem `projection_fill` in der Navigation darf `projectionStageIndex === -1` nicht in die Projektions-Phase springen (Regressionstest in `spatialSequenceWorkshopPhase.test.ts`).

## Didaktische Schutzregeln (workshop_v2)

| Kapitel | Regel |
|---------|--------|
| 2 Netz | Faltvorschau nur nach «Hilfe: Faltvorschau» (nicht live beim Markieren); Validate: erst Entscheid-Phase |
| 1 Würfel/Bild | Erkunden in Schritt 1 (Drehen); ab «Weiter zur Auswahl» Kamera gesperrt (`cameraLocked`) |

## Manuelle Verifikation (pro Kapitel-Pilot)

Nach grüner CI: Freischaltung, Overlay-Wahrheitstabelle (Kap. 3), Pfeilrichtungen am Guide — bevor das nächste Kapitel startet.
