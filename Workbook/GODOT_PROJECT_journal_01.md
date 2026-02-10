# Godot Project Workbook

## Location
- `game/crystal-heart`

## Engine / Project Settings
- Project name: CrystalHeart
- Main scene: `crystal_heart.tscn`
- Godot version feature set: 4.6 (Forward Plus)
- Physics engine: Jolt Physics

## Scene Overview: `crystal_heart.tscn`
- Root: `CrystalHeart` (Node2D)
- `CrystalLayer` (Node2D)
  - Script: `crystal_layer.gd`
  - `CrystalArea` (Area2D)
    - `CrystalShape` (CollisionPolygon2D)
  - `CrystalFill` (Polygon2D)
  - `CrystalPoints` (Node)
    - Script: `crystal_points.gd`
    - `vertex_points`: a square-like polygon (4 points)
- `Camera2D`

## Script Summary

### `crystal_layer.gd`
- Grabs references to the collision polygon, visual polygon, and `CrystalPoints` node.
- On `_ready()`, calls `set_shape()` with the `vertex_points` from `CrystalPoints`.
- `set_shape()` assigns the same polygon to both the collision and visual fill.
- `_process()` is currently idle (commented out).

### `crystal_points.gd`
- Stores exported `vertex_points` and computed `side_mid_points`.
- On `_ready()`, computes midpoints for each edge of `vertex_points`.
- `set_mid_points()` loops through all vertices and appends midpoint for each edge, wrapping the last to the first.
- Includes `print_mid_points()` helper for debugging.

## Current Behavior (So Far)
- The scene displays a polygon (`CrystalFill`) and a matching collision shape (`CrystalShape`) based on `vertex_points`.
- A `CrystalPoints` node computes midpoints for each polygon edge at startup, but those midpoints are not yet used elsewhere.
- No runtime animation or updates are active yet.

## Notes / Next Likely Steps
- Hook `side_mid_points` into visuals or gameplay (e.g., vertex handles, effects, or procedural growth).
- Drive `set_shape()` from `_process()` or a signal if the vertex list becomes dynamic.
- Consider adding debug draw or gizmos for midpoints if they become important to editing.
