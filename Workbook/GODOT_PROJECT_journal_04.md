# Godot Project Journal 04

## Date
- 2026-02-11

## Scope
- Read current Godot project state and record changes since Journal 03.

## Current State
- Project: `game/crystal-heart`
- Main scene: `crystal_heart.tscn`
- Core nodes in main scene: `CrystalLayer`, `CrystalArea`, `CrystalShape`, `CrystalFill`, `CrystalPoints`, `EmitterArray`, `Camera2D`
- `CrystalLayer` sets up emitters at crystal vertex points and pushes them into `EmitterArray`.
- `EmitterArray` steps and renders particles, renders emitter gizmos, and spawns new particles on a timer.

## Changes Since Journal 03
- Naming cleanup:
  - `emmitter.gd` -> `emitter.gd`
  - `emmitter_array.gd` -> `emitter_array.gd`
  - `EmmitterArray` -> `EmitterArray`
  - `LiquidEmmitter` -> `LiquidEmitter`
  - `emmit_*` -> `emit_*`
- `crystal_layer.gd` updates:
  - Export flag renamed to `emit_ready`.
  - Uses `EmitterArray` and `LiquidEmitter` with `set_up_emitters()`.
- `emitter_array.gd` updates:
  - Added `emit_base_speed` and shorter `count_down` (0.1).
  - `emit_particles()` now spawns with a fixed speed of 10.
- `emitter.gd` updates:
  - Added angular variance (`emit_angular_varience`) for spray.
  - Added `emit_many()` helper to create multiple particles.

## Notes
- `emit_base_speed` is declared but not yet used in `emit_particles()`.
- If you want more control, consider threading `emit_base_speed` into `emit_particles()`.
