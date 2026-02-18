# Godot Project Journal 06

## Date
- 2026-02-15

## Scope
- Record real project changes since `GODOT_PROJECT_journal_05.md`.

## Current State Snapshot
- Main scene: `crystal_heart.tscn` now includes scripts for `CrystalLayer`, `EmitterArray`, and `Lattice`.
- Crystal shape starts as `PackedVector2Array(60, 30, 60, -30, 0, -30, 0, 30)` in the main scene.
- A reusable layer scene now exists at `crystal_layer.tscn` to support spawning the next crystal layer.

## Changes Since Journal 05
- `crystal_layer.gd`
- Added crystallization lifecycle flags and timing: `crystalizing`, `fully_crystalized`, `time_till_crystalize`, `crystalization_count_down`.
- Added support for deferred initialization with `initialize_with_points()` and pending point storage.
- `set_shape()` now updates points via `crystal_points.set_vertex_points()` before collision/visual polygon assignment.
- Added full cycle methods: `crystalize()`, `handle_crystalization_complete()`, and `spawn_next_crystal_layer()`.
- Emitter setup is now directional by geometry:
- Vertex emitters use outward center-based angle (`get_vertex_half_angle()`).
- Midpoint emitters use edge/outward tangent logic (`get_edge_tangent_angle()`).

- `crystal_points.gd`
- Added `set_vertex_points()` to safely replace polygon data and recompute side midpoints.

- `emitter_array.gd`
- Added crystalizing-mode behavior split:
- Normal mode attracts particles toward local shape segments.
- Crystalizing mode repels particles outward from crystal center (`apply_crystalize_repel`).
- Added minimum age gate (`spawn_force_delay_seconds`) before attract/repel and pairwise interactions apply.
- Added `clear_particles()` and wiring for crystalization handoff.
- Emission now uses crowd-adjusted speed directly via `emitter.emit_one(speed)`.

- `fluid_particle.gd`
- Defaults were hardened (`pos`, `vel`, and `parent_emmiter_index = -1`).
- Death condition now includes out-of-bounds check (`pos.x < 0`) in addition to lifetime.
- `combine_velocities()` remains present as a helper; interaction path still uses `attract_repulse()`.

- `emitter.gd`
- Simplified emitter API to `emit_one(speed)` and `emit_many(count, speed)`.
- Emitter `size` remains used by crowding logic in `EmitterArray`.

- `lattice.gd`
- Upgraded from placeholder to full crystallization system.
- Tracks frontier slots and placed lattice particles, converts nearby fluid particles, and completes after inactivity timeout.
- Builds next polygon from placed particles with perimeter reconstruction/simplification and area guards.
- Calls back into `CrystalLayerControl.handle_crystalization_complete(...)` on completion.

## Notes
- Identifier spelling still mixes `emmiter`/`emitter` in some variable and method names.
- `lattice_particle.gd`, `lattice_slot.gd`, and `lattice_perimeter_sample.gd` are present and support lattice runtime types.
