# Generischer Gebäude-Renderer (Raumgeometrie)

Status: **Phase 1–2 umgesetzt** in Code; Phase 3–4 siehe Ausblick unten.

## Prinzip

Die KI erzeugt **keinen** ausführbaren Code pro Einheit. Sie liefert strukturierte Daten
(Höhenmatrix, Farben, Template-ID) — feste, getestete Komponenten rendern und prüfen
(dasselbe Muster wie `grid_fill` / `region_paint`).

## Implementiert

| Baustein | Pfad |
|----------|------|
| Isometrie + Layout aus Matrix | `backend/app/core/iso_building.py` |
| Legacy-Templates (`iso_single_cube`, `iso_tower_2`) | berechnet via `region_layouts.get_region_template()` |
| `building_paint` (Parser, Grading, Trainer) | `spatial_compact.py`, `RegionPaintExercise` |
| `grid_fill` + `validation: derived_projection` | Parser + `score_derived_projection_answer` |
| TS-Renderer (Client) | `frontend/src/lib/isoBuilding.ts` |
| Würfelnetz (Topologie, 6 Zellen) | `valid_cube_net()` — Basis für Phase 3 |

### `building_paint` (Schema)

```json
{
  "answer_type": "building_paint",
  "height_matrix": [[2,1],[1,3]],
  "colored_faces": {"0,0,1,top": "yellow"},
  "palette": ["yellow", "green", "purple"]
}
```

Flächen-IDs: `x,y,z,top|left|right` (berechnet, nicht handgezeichnet).

### `derived_projection`

`grid_fill_items` mit `validation: "derived_projection"` und `answer.height_matrix` —
Lösung des Lernenden ist eine Höhenmatrix; Vergleich über `building_projections()`.

## Phasenplan (offen)

1. ~~Genereller Renderer + Template-Migration~~ (erledigt)
2. ~~`derived_projection` in `grid_fill`~~ (Backend; dedizierte UI optional)
3. **Netz-Antippen** (`net_build`) + Quader-Grössencheck auf `valid_cube_net`
4. **Synthetischer Standpunkt** (Ergänzung zu `point_on_image`, nicht Ersatz)

## Architektur

Rendering **clientseitig** (SVG `viewBox`, skalierbar). Backend validiert Matrizen
und erwartete Farben/Ansichten — keine SVG-Generierung im API.

Maximale Matrixgrösse Gebäude: **8×8**, Stapelhöhe **12** (`iso_building.py`).
