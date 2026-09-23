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

Generische Freischaltung: `frontend/src/lib/workshop/` (`workshopCapabilities`, `useWorkshopFlow`).

## Backend

- `spatial_sequence.expected_visibility` — aus `compute_visibility_decision`, für UI-Feedback (nicht für End-Score allein).
- Antwort-JSON unverändert: `visibility` + `projections`.

## Schema (additiv)

- `grid_fill.presentation: "workshop_v2"` — Werkstatt-UI für Bauplan (`derived_projection` + `reference_height_matrix`).
- `synthetic_viewpoint.presentation: "workshop_v2"` — zweistufig: Schrägansicht, dann Standort-Wahl.
- `spatial_sequence` — unverändert; gleiches Capability-Muster wie bisher.

## Weitere Modi (geplant)

`building_paint` (farbige Projektionen), Kap. 2 Netze (`cube_net_cell_face_mapping` im Backend).

Kap. 3: `resolveSpatialSequenceWorkshopPhase` — bei fehlendem `projection_fill` in der Navigation darf `projectionStageIndex === -1` nicht in die Projektions-Phase springen (Regressionstest in `spatialSequenceWorkshopPhase.test.ts`).

## Manuelle Verifikation (pro Kapitel-Pilot)

Nach grüner CI: Freischaltung, Overlay-Wahrheitstabelle (Kap. 3), Pfeilrichtungen am Guide — bevor das nächste Kapitel startet.
