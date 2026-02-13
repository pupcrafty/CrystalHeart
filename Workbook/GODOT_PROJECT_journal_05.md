# Godot Project Journal 05

## Date
- 2026-02-12

## Scope
- Capture real project changes since Journal 04 by reading current scripts and scene.

## Current State
- Project: `game/crystal-heart`
- Main scene: `crystal_heart.tscn`
- `CrystalLayer` now seeds emitters from both `vertex_points` and `side_mid_points`.
- `EmitterArray` now handles particle stepping, pairwise interactions, crowd-based emit-speed logic scaffolding, and shape-attraction.
- `FluidParticle` now includes emitter parent tracking, interaction physics, and velocity blending helper APIs.

## Changes Since Journal 04
- `crystal_layer.gd`
- Added `crystalizing` export flag.
- `emit_ready` defaults to `true`.
- `set_up_emitters()` now creates emitters at both vertex and midpoint positions.

- `crystal_heart.tscn`
- Added `Lattice` node under `CrystalLayer`.
- Scene still wires `EmitterArray` as active particle manager.

- `emitter_array.gd`
- Added `emit_crowd_multiplier` and emitter crowd counting via `get_emmiter_crowd()`.
- Added `apply_particle_interactions()` to run pairwise particle interactions each frame.
- Added `apply_shape_attract()` with nearest-emitter-segment projection using `closest_two()` and `closest_point_on_emmiter_segment()`.
- Emission now tracks `parent_emmiter_index` per particle.

- `fluid_particle.gd`
- Added exported `parent_emmiter_index`.
- Added interaction pipeline: `interact()` and `attract_repulse()`.
- Added `combine_velocities(particle, intensity)` helper to blend two particle velocities.
- Added `attract_to_shape_point()` to pull particles toward a shape target.
- Particle lifetime increased to `120.0`; damping set to `deceleraton = 0.1`.

- `emitter.gd`
- `LiquidEmitter` now emits with optional Y-velocity offset (`emit_one(speed, y_vel_off_set)`).
- Added emitter `size` field.

- `lattice.gd`
- New placeholder script exists; no active logic yet.

## Notes
- `combine_velocities()` exists but is not called from `interact()` yet.
- `emit_particles()` calculates crowd-adjusted `speed` but currently passes `emit_base_speed` into `emit_one()`.
- Spelling variants remain (`emmiter` in some identifiers), but runtime naming is internally consistent.
