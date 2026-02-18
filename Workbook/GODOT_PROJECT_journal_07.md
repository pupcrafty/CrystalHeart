# Godot Project Journal 07

## Date
- 2026-02-18

## Scope
- Record real project updates since `GODOT_PROJECT_journal_06.md`.

## Current State Snapshot
- Project: `game/crystal-heart`
- Main scene now renders crystal growth through a `SubViewport` (`CrystalGrowth`) and displays it via two `Sprite2D` mirrors (`CrystalViewLeft`, `CrystalViewRight`).
- `CrystalLayer` is now parented under `CrystalGrowth` instead of directly under root.

## Changes Since Journal 06
- `crystal_heart.tscn`
- Added `SubViewport` pipeline:
- `CrystalGrowth` (`SubViewport`) hosts `CrystalLayer`.
- `CrystalViewLeft` and `CrystalViewRight` display `ViewportTexture` from `CrystalGrowth`.
- Added `FileOutput` node under `CrystalGrowth/CrystalLayer`.

- `crystal_layer.gd`
- Added color cycling for crystal layers via exported `shape_colors` and `get_next_shape_color()`.
- Added previous-shape overlay archiving with `PreviousShapeOverlays` container and `add_previous_shape_overlay()`.
- Added `max_previous_shape_overlays` cap to limit retained overlays.
- Crystallization completion flow changed:
- No longer spawns/replaces with a new layer scene.
- Now archives current polygon/color, clears particles, and applies `new_vertex_points` on the same node.
- Integrated file output hook:
- On crystallization completion, calls `file_output.save_replaced_shape(previous_points, vis_poly.color)` when available.

- `file_output.gd` (new)
- Added run-based JSON export of replaced shapes to `user://crystal_shapes/<run_id>/shapes.json`.
- Stores shape index, timestamp, RGBA color, and serialized polygon points.
- Automatically initializes a new run in `_ready()`.

- `crystal_layer.tscn`
- Updated reusable layer scene to include `FileOutput` node/script.

- `project.godot`
- Added display settings:
- `window/size/viewport_width=1024`
- `window/size/viewport_height=600`
- `window/size/resizable=false`

- `audio_service/` (new folder)
- Added `audio_service_osc.gd` OSC receiver utility and local `README.md`.
- This appears staged for integration; no active references found in current scene/scripts.

## Notes
- `crystal_layer.gd` still exposes `emit_ready`, but emitter flow is effectively driven by the crystallization timer and state flags.
- `audio_service` is present but not yet wired into `crystal_heart.tscn` or the active crystal scripts.
