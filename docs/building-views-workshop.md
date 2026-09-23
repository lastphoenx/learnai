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

Generische Freischaltung: `frontend/src/lib/workshop/` (`workshopCapabilities`, `useWorkshopFlow`).

## Backend

- `spatial_sequence.expected_visibility` — aus `compute_visibility_decision`, für UI-Feedback (nicht für End-Score allein).
- Antwort-JSON unverändert: `visibility` + `projections`.

## Schema (additiv)

- `grid_fill.presentation: "workshop_v2"` — Werkstatt-UI für Bauplan (`derived_projection` + `reference_height_matrix`).
- `spatial_sequence` — unverändert; gleiches Capability-Muster wie bisher.

## Weitere Modi (geplant)

`building_paint` (farbige Projektionen), Kap. 6 `synthetic_viewpoint`, Kap. 2 Netze (`cube_net_cell_face_mapping` im Backend).

## Manuelle Verifikation (pro Kapitel-Pilot)

Nach grüner CI: Freischaltung, Overlay-Wahrheitstabelle (Kap. 3), Pfeilrichtungen am Guide — bevor das nächste Kapitel startet.
