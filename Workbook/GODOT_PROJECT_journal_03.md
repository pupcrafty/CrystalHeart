# Godot Project Journal 03

## Date
- 2026-02-11

## Scope
- Read current Godot project state and record changes since Journal 02.

## Current State
- Project: `game/crystal-heart`
- Main scene: `crystal_heart.tscn`
- Core nodes in main scene: `CrystalLayer`, `CrystalArea`, `CrystalShape`, `CrystalFill`, `CrystalPoints`, `EmitterArray`, `Camera2D`
- `CrystalLayer` now references `EmitterArray` and sets up emitters at the crystal vertex points.
- `EmitterArray` now manages both particles and emitters, drawing both each frame and emitting particles on a timer.

## Changes Since Journal 02
- Scene graph update: added `EmitterArray` node in `crystal_heart.tscn` and linked `emitter_array.gd`.
- `crystal_layer.gd` updates:
  - Added `class_name CrystalLayerControl`.
  - Added `EmitterArray` reference and `set_up_emitters()` to create emitters from crystal vertices.
  - Emits use `LiquidEmitter` instances with angle based on vertex direction.
- `emitter_array.gd` updates:
  - Added `emitters` list and emission timer (`count_down`).
  - `emit_particles()` now spawns particles from each emitter every second.
  - `_draw()` now renders both particles and emitters.
- `emitter.gd` refactor:
  - Now defines `class_name LiquidEmitter` (no longer a Node2D script).
  - `emit_one()` now returns a `FluidParticle` with velocity from `emit_angle`.
- `fluid_particle.gd` tuning:
  - Deceleration and lifetime adjusted; `step()` now blends velocity toward zero without console logging.

## Notes
- The particle system is now connected to the main scene via `EmitterArray`.
- Spelling now uses `emitter` in filenames and class names.
