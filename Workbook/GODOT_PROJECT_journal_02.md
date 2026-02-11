# Godot Project Journal 02

## Date
- 2026-02-10

## Scope
- Read the Godot project and record actual current state and changes.

## Current State
- Project: `game/crystal-heart`
- Main scene: `crystal_heart.tscn`
- Core nodes in main scene: `CrystalLayer`, `CrystalArea`, `CrystalShape`, `CrystalFill`, `CrystalPoints`, `Camera2D`
- Behavior: `CrystalLayer` uses `CrystalPoints.vertex_points` to set both collision and visual polygons.
- `CrystalPoints` computes edge midpoints on `_ready()`; midpoints are not yet consumed elsewhere.

## Particle System (New)
- `emitter_array.gd` defines `EmitterArray` (Node2D) that stores `FluidParticle` instances, steps them each frame, removes dead ones, and draws them.
- `emitter.gd` defines a Node2D that spawns one `FluidParticle` on `_ready()` and draws a red circle at its position.
- `fluid_particle.gd` defines `FluidParticle` with position, velocity, deceleration, lifetime, and step/dead logic.
- These scripts are present in the project folder but are not referenced by the main scene yet.

## Changes Since Journal 01
- Added particle-related scripts:
  - `emitter.gd`
  - `emitter_array.gd`
  - `fluid_particle.gd`
- No changes detected in the main scene structure (`crystal_heart.tscn`).

## Notes
- If the particle system should be visible in-game, it needs nodes in `crystal_heart.tscn` that use `EmitterArray` and `Emitter` scripts.
- Spelling: filenames use `emitter`.
