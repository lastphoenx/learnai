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
| `SpatialSequenceExercise` | Erster Konsument des Templates |

## Backend

- `spatial_sequence.expected_visibility` — aus `compute_visibility_decision`, für UI-Feedback (nicht für End-Score allein).
- Antwort-JSON unverändert: `visibility` + `projections`.

## Weitere Modi (geplant)

`grid_fill`, `building_paint` (farbige Projektionen) können dieselbe Shell mit anderem `projectionsBlock` nutzen.
