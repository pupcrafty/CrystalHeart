# Godot Project Journal 08

## Date
- 2026-02-18

## Scope
- Record real project updates since `GODOT_PROJECT_journal_07.md`.

## Current State Snapshot
- Main scene still uses the `SubViewport` crystal render pipeline (`CrystalGrowth` -> mirrored sprites).
- Audio integration is now active in the scene with runtime OSC input and on-screen debug visualization.

## Changes Since Journal 07
- `crystal_heart.tscn`
- Added active audio nodes at scene root:
- `AudioServiceOSC` (script: `audio_service/audio_service_osc.gd`)
- `AudioDebugDisplay` (script: `audio_service_debug_display.gd`)
- Added debug UI hierarchy:
- `AudioDebugDisplay/MarginContainer/DebugLabel`
- `AudioServiceOSC.endpoint_names` is explicitly configured to:
- `/clock/bpm`
- `/clock/beat`
- `/clock/conf`
- `/clock/beat_id`
- `/clock/time`
- `/audio/bands_normalized`
- Updated initial crystal polygon in `CrystalPoints.vertex_points` to a more detailed 10-point shape.

- `audio_service_debug_display.gd` (new)
- Added `CanvasLayer` debug panel that refreshes every `refresh_interval`.
- Pulls `/audio/bands_normalized` via `get_normalized_bands()` from `AudioServiceOSC`.
- Sorts bands by `normalized` descending and displays top N (`max_bands_to_show`).
- Displays clock context (`bpm`, `beat_id`) and active/total band counts.

- `audio_service/audio_service_osc.gd`
- Continues as OSC receiver utility, now actively referenced by `crystal_heart.tscn`.
- Message polling is non-blocking and parses float/int/string (including JSON payloads).
- Includes normalized-band normalization helper: `get_normalized_bands()`.

## Notes
- This resolves the prior state from Journal 07 where `audio_service` existed but was not wired into the main scene.
- `crystal_layer.gd`, `emitter_array.gd`, `lattice.gd`, and `project.godot` appear unchanged relative to Journal 07 for core behavior.
