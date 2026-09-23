# Generischer Gebäude-Renderer (Raumgeometrie)

**Stand:** Phase 1–2 + **Phase 3/4 (Basis)** + **Spalten-Inspektor (§9)**.

## Umgesetzt

| Phase | Inhalt |
|-------|--------|
| 1 | `iso_building.py`, `isoBuilding.ts`, Legacy-Templates berechnet |
| 2 | `building_paint`, `grid_fill` + `derived_projection`, `reference_height_matrix` |
| 3 | `net_build` + `valid_cube_net`, UI `NetBuildExercise` |
| 4 (Basis) | `synthetic_viewpoint` + `SyntheticViewpointExercise` (Iso-Szene, keine Fotos) |
| §9 | `buildColumnInspector`, `classifyColumnVisibility`, Rückansicht (`camera: back`), `BuildingIsoPreview` in Grid/Region |

## Spalten-Inspektor

- **Schrägansicht allein** kann Spalten verdecken → Hinweis + optional **Rückansicht**.
- **Spalte A…** öffnet Marker (Tiefe 1–n), massgebliche Tiefe hervorgehoben.
- Backend: `classify_column_visibility(matrix)` für QA/Generierung.

## Offen (bewusst)

- Quader-Netze (Rechteckgrössen pro Fläche)
- Vollständiger Normalen-BFS für `valid_cube_net` (aktuell: Zusammenhang + Grad)
- Prozedural zufällige Standpunkt-Szenen in der **Generierung** (nur Schema/UI)

## Referenz

Siehe ursprüngliche Spezifikation (Phasenplan §8, Zuordnungstabelle §5) im Team-Chat / Ticket.
