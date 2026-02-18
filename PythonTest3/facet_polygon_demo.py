#!/usr/bin/env python3
"""Render layered crystal shapes from Godot shapes.json.

- Reads a run JSON (either explicit --input or latest run under Godot app_userdata).
- Facets each shape interior with deterministic shard triangles.
- Layers all shapes so smaller/older shapes are drawn on top by default.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import math
from dataclasses import dataclass
from pathlib import Path


GODOT_SHAPES_ROOT = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Godot"
    / "app_userdata"
    / "CrystalHeart"
    / "crystal_shapes"
)


@dataclass(frozen=True)
class Vec2:
    x: float
    y: float

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> "Vec2":
        length = self.length()
        if length <= 1e-8:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / length, self.y / length)

    def to_svg(self) -> str:
        return f"{self.x:.2f},{self.y:.2f}"


@dataclass
class ShapeLayer:
    index: int
    saved_unix: float
    points: list[Vec2]
    area: float
    color_rgba: tuple[float, float, float, float] | None = None


@dataclass
class FacetSet:
    facets: list[tuple[list[Vec2], float]]
    core_polygon: list[Vec2] | None = None


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def polygon_area(points: list[Vec2]) -> float:
    area2 = 0.0
    n = len(points)
    for i in range(n):
        a = points[i]
        b = points[(i + 1) % n]
        area2 += a.x * b.y - b.x * a.y
    return area2 * 0.5


def ensure_ccw(points: list[Vec2]) -> list[Vec2]:
    if polygon_area(points) < 0.0:
        return list(reversed(points))
    return points[:]


def polygon_center(points: list[Vec2]) -> Vec2:
    n = len(points)
    if n == 0:
        return Vec2(0.0, 0.0)
    return Vec2(sum(p.x for p in points) / n, sum(p.y for p in points) / n)


def bounds(points: list[Vec2]) -> tuple[float, float, float, float]:
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def translated(points: list[Vec2], dx: float, dy: float) -> list[Vec2]:
    return [Vec2(p.x + dx, p.y + dy) for p in points]


def svg_polygon(
    points: list[Vec2],
    fill: str,
    stroke: str,
    stroke_width: float = 1.0,
    fill_opacity: float | None = None,
) -> str:
    coords = " ".join(p.to_svg() for p in points)
    fill_opacity_attr = ""
    if fill_opacity is not None:
        fill_opacity_attr = f' fill-opacity="{clamp01(fill_opacity):.3f}"'
    return (
        f'<polygon points="{coords}" fill="{fill}"{fill_opacity_attr} '
        f'stroke="{stroke}" stroke-width="{stroke_width:.2f}" />'
    )


def hsl_to_hex(h: float, s: float, l: float) -> str:
    h = h % 360.0
    s = clamp01(s)
    l = clamp01(l)
    c = (1.0 - abs(2.0 * l - 1.0)) * s
    hp = h / 60.0
    x = c * (1.0 - abs(hp % 2.0 - 1.0))

    if 0.0 <= hp < 1.0:
        r1, g1, b1 = c, x, 0.0
    elif 1.0 <= hp < 2.0:
        r1, g1, b1 = x, c, 0.0
    elif 2.0 <= hp < 3.0:
        r1, g1, b1 = 0.0, c, x
    elif 3.0 <= hp < 4.0:
        r1, g1, b1 = 0.0, x, c
    elif 4.0 <= hp < 5.0:
        r1, g1, b1 = x, 0.0, c
    else:
        r1, g1, b1 = c, 0.0, x

    m = l - c * 0.5
    r = int(round((r1 + m) * 255.0))
    g = int(round((g1 + m) * 255.0))
    b = int(round((b1 + m) * 255.0))
    return f"#{r:02x}{g:02x}{b:02x}"


def wrap_hue(h: float) -> float:
    return h % 360.0


def rgb_to_hsl(r: float, g: float, b: float) -> tuple[float, float, float]:
    h, l, s = colorsys.rgb_to_hls(clamp01(r), clamp01(g), clamp01(b))
    return h * 360.0, s, l


def deterministic_noise(index: int, seed: int) -> float:
    value = math.sin((index * 12.9898 + seed * 78.233) * 0.91) * 43758.5453
    return value - math.floor(value)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def cross(a: Vec2, b: Vec2) -> float:
    return a.x * b.y - a.y * b.x


def support_radius(points: list[Vec2], center: Vec2, direction: Vec2) -> float:
    # Ray-polygon intersection gives a truer boundary support than vertex projection.
    n = len(points)
    if n < 2:
        return 0.0
    best_t = 0.0
    for i in range(n):
        a = points[i]
        b = points[(i + 1) % n]
        edge = b - a
        rel = a - center
        denom = cross(direction, edge)
        if abs(denom) <= 1e-8:
            continue
        t = cross(rel, edge) / denom
        u = cross(rel, direction) / denom
        if t >= 0.0 and 0.0 <= u <= 1.0:
            if t > best_t:
                best_t = t

    if best_t > 0.0:
        return best_t

    # Fallback for degenerate/parallel cases.
    max_proj = 0.0
    for p in points:
        proj = (p - center).x * direction.x + (p - center).y * direction.y
        if proj > max_proj:
            max_proj = proj
    return max_proj


def stabilize_layers_against_previous(
    layers: list[ShapeLayer],
    strength: float,
    max_growth_ratio: float,
) -> list[ShapeLayer]:
    if len(layers) <= 1:
        return layers[:]

    strength = clamp01(strength)
    max_growth_ratio = max(1.0, max_growth_ratio)
    order = sorted(range(len(layers)), key=lambda i: (layers[i].index, layers[i].saved_unix))
    out = layers[:]

    anchor_center = polygon_center(out[order[0]].points)

    for seq_idx in range(1, len(order)):
        prev_idx = order[seq_idx - 1]
        curr_idx = order[seq_idx]
        prev_layer = out[prev_idx]
        curr_layer = out[curr_idx]
        center = anchor_center

        adjusted: list[Vec2] = []
        adjusted_radii: list[float] = []
        adjusted_dirs: list[Vec2] = []
        for p in curr_layer.points:
            radial = p - center
            radius = radial.length()
            if radius <= 1e-6:
                adjusted.append(p)
                adjusted_radii.append(0.0)
                adjusted_dirs.append(Vec2(0.0, 0.0))
                continue
            direction = radial.normalized()
            prev_radius = support_radius(prev_layer.points, center, direction)
            allowed = prev_radius * max_growth_ratio
            target_radius = min(radius, allowed) if prev_radius > 0.0 else radius
            final_radius = lerp(radius, target_radius, strength)
            adjusted_radii.append(final_radius)
            adjusted_dirs.append(direction)
            adjusted.append(center + direction * final_radius)

        # Smooth spikes so outer layers do not form long directional protrusions.
        if len(adjusted_radii) >= 3:
            smoothed: list[float] = adjusted_radii[:]
            count = len(adjusted_radii)
            for i in range(count):
                prev_r = adjusted_radii[(i - 1 + count) % count]
                curr_r = adjusted_radii[i]
                next_r = adjusted_radii[(i + 1) % count]
                avg = prev_r * 0.25 + curr_r * 0.5 + next_r * 0.25
                smoothed[i] = min(curr_r, avg * 1.04)
            adjusted = []
            for i, direction in enumerate(adjusted_dirs):
                if direction.length() <= 1e-6:
                    adjusted.append(center)
                else:
                    adjusted.append(center + direction * smoothed[i])

        adjusted = ensure_ccw(adjusted)
        out[curr_idx] = ShapeLayer(
            index=curr_layer.index,
            saved_unix=curr_layer.saved_unix,
            points=adjusted,
            area=abs(polygon_area(adjusted)),
            color_rgba=curr_layer.color_rgba,
        )

    return out


def build_gem_facets(points: list[Vec2], seed: int) -> FacetSet:
    n = len(points)
    if n < 3:
        return FacetSet(facets=[(points[:], 0.0)], core_polygon=None)
    center = polygon_center(points)

    inner_ring: list[Vec2] = []
    for i in range(n):
        a = points[i]
        b = points[(i + 1) % n]
        mid = Vec2((a.x + b.x) * 0.5, (a.y + b.y) * 0.5)
        radial = mid - center
        ratio = 0.38 + deterministic_noise(i, seed) * 0.20
        inner_ring.append(center + radial * ratio)

    facets: list[tuple[list[Vec2], float]] = []
    for i in range(n):
        a = points[i]
        b = points[(i + 1) % n]
        inner_curr = inner_ring[i]
        inner_prev = inner_ring[(i - 1 + n) % n]
        inner_next = inner_ring[(i + 1) % n]

        facets.append(([a, b, inner_curr], 0.00))
        facets.append(([inner_prev, inner_curr, center], 0.04))
        facets.append(([inner_curr, inner_next, center], 0.04))
    return FacetSet(facets=facets, core_polygon=None)


def build_geode_facets(points: list[Vec2], seed: int) -> FacetSet:
    n = len(points)
    if n < 3:
        return FacetSet(facets=[(points[:], 0.0)], core_polygon=None)
    center = polygon_center(points)

    mid_ring: list[Vec2] = []
    inner_ring: list[Vec2] = []
    core_ring: list[Vec2] = []
    for i in range(n):
        a = points[i]
        b = points[(i + 1) % n]
        mid = Vec2((a.x + b.x) * 0.5, (a.y + b.y) * 0.5)
        radial = mid - center
        # Thicker chunks: push rings outward and reduce jitter.
        mid_ring.append(center + radial * (0.80 + deterministic_noise(i + 17, seed) * 0.05))
        inner_ring.append(center + radial * (0.58 + deterministic_noise(i + 53, seed) * 0.08))
        core_ring.append(center + radial * (0.34 + deterministic_noise(i + 101, seed) * 0.05))

    facets: list[tuple[list[Vec2], float]] = []
    for i in range(n):
        a = points[i]
        b = points[(i + 1) % n]
        mid = mid_ring[i]
        inner = inner_ring[i]
        inner_next = inner_ring[(i + 1) % n]
        core = core_ring[i]

        # Outer rim facets: darker geode shell.
        facets.append(([a, b, mid], -0.12))
        # Thick middle crystal chunks (bigger quads split as triangles).
        facets.append(([a, mid, inner], -0.02))
        facets.append(([mid, b, inner_next], 0.00))
        # Broad inner chunks.
        facets.append(([inner, inner_next, core], 0.14))

    return FacetSet(facets=facets, core_polygon=core_ring)


def facet_color(
    tri: list[Vec2],
    center: Vec2,
    hue: float,
    sat: float,
    facet_index: int,
    layer_depth_01: float,
    facet_bias: float,
) -> tuple[str, float]:
    tri_center = polygon_center(tri)
    radial = tri_center - center
    dist = radial.length()
    dir_v = radial.normalized()
    light_dir = Vec2(-0.76, -0.42).normalized()
    facing = clamp01((dir_v.x * light_dir.x + dir_v.y * light_dir.y + 1.0) * 0.5)
    depth = clamp01(dist / 260.0)
    alternating = 0.06 if facet_index % 2 == 0 else -0.03
    layer_bias = (0.5 - layer_depth_01) * 0.12
    lightness = clamp01(
        0.22 + 0.45 * facing + 0.20 * (1.0 - depth) + alternating + layer_bias + facet_bias
    )
    return hsl_to_hex(hue, sat, lightness), lightness


def find_latest_shapes_json(root: Path) -> Path:
    run_dirs = [p for p in root.glob("run_*") if p.is_dir()]
    if not run_dirs:
        raise FileNotFoundError(f"No run_* folders found under {root}")
    latest = max(run_dirs, key=lambda p: p.stat().st_mtime)
    path = latest / "shapes.json"
    if not path.exists():
        raise FileNotFoundError(f"No shapes.json in {latest}")
    return path


def resolve_input_path(input_value: str | None) -> Path:
    if not input_value:
        return find_latest_shapes_json(GODOT_SHAPES_ROOT)
    path = Path(input_value).expanduser()
    if path.is_dir():
        path = path / "shapes.json"
    if not path.exists():
        raise FileNotFoundError(f"Input path not found: {path}")
    return path


def load_shape_layers(json_path: Path) -> tuple[str, list[ShapeLayer]]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    run_id = str(payload.get("run_id", json_path.parent.name))
    raw_shapes = payload.get("shapes", [])

    layers: list[ShapeLayer] = []
    for entry in raw_shapes:
        raw_points = entry.get("points", [])
        points = [Vec2(float(p["x"]), float(p["y"])) for p in raw_points if "x" in p and "y" in p]
        if len(points) < 3:
            continue
        points = ensure_ccw(points)
        area = abs(polygon_area(points))
        color_rgba: tuple[float, float, float, float] | None = None
        raw_color = entry.get("color")
        if isinstance(raw_color, dict):
            if all(k in raw_color for k in ("r", "g", "b", "a")):
                color_rgba = (
                    float(raw_color["r"]),
                    float(raw_color["g"]),
                    float(raw_color["b"]),
                    float(raw_color["a"]),
                )
        layers.append(
            ShapeLayer(
                index=int(entry.get("index", len(layers) + 1)),
                saved_unix=float(entry.get("saved_unix", 0.0)),
                points=points,
                area=area,
                color_rgba=color_rgba,
            )
        )

    if not layers:
        raise ValueError(f"No valid shapes in {json_path}")
    return run_id, layers


def build_canvas(layers: list[ShapeLayer], pad: float) -> tuple[float, float, float, float, float, float]:
    min_x = min(min(p.x for p in layer.points) for layer in layers)
    min_y = min(min(p.y for p in layer.points) for layer in layers)
    max_x = max(max(p.x for p in layer.points) for layer in layers)
    max_y = max(max(p.y for p in layer.points) for layer in layers)

    width = (max_x - min_x) + pad * 2.0
    height = (max_y - min_y) + pad * 2.0
    dx = pad - min_x
    dy = pad - min_y
    return width, height, min_x, min_y, dx, dy


def growth_sorted_layers(layers: list[ShapeLayer]) -> list[ShapeLayer]:
    return sorted(layers, key=lambda s: (s.index, s.saved_unix))


def radial_resample(points: list[Vec2], center: Vec2, sample_count: int) -> list[Vec2]:
    out: list[Vec2] = []
    for i in range(sample_count):
        theta = (i / sample_count) * math.tau
        direction = Vec2(math.cos(theta), math.sin(theta))
        radius = support_radius(points, center, direction)
        out.append(center + direction * radius)
    return out


def render_accretion_layers(
    shifted_growth_layers: list[ShapeLayer],
    fallback_hue: float,
    fallback_sat: float,
    seed: int,
    sample_count: int,
) -> tuple[list[str], list[str]]:
    if len(shifted_growth_layers) == 0:
        return [], []
    if len(shifted_growth_layers) == 1:
        only = shifted_growth_layers[0]
        layer_hue = fallback_hue
        layer_sat = fallback_sat
        layer_alpha = 0.85
        if only.color_rgba is not None:
            r, g, b, a = only.color_rgba
            h_from_json, s_from_json, _l = rgb_to_hsl(r, g, b)
            layer_hue = h_from_json
            layer_sat = max(0.25, s_from_json)
            layer_alpha = clamp01(a)
        return [], [svg_polygon(only.points, hsl_to_hex(layer_hue, layer_sat * 0.6, 0.46), "#edf4ff", 1.4, layer_alpha)]

    center = polygon_center(shifted_growth_layers[0].points)
    defs: list[str] = []
    chunks: list[str] = []
    seam_lines: list[str] = []

    section_count = 8
    section_size = max(1, sample_count // section_count)
    for band_index in range(1, len(shifted_growth_layers)):
        prev_layer = shifted_growth_layers[band_index - 1]
        curr_layer = shifted_growth_layers[band_index]
        prev_resampled = radial_resample(prev_layer.points, center, sample_count)
        curr_resampled = radial_resample(curr_layer.points, center, sample_count)

        layer_hue = fallback_hue
        layer_sat = fallback_sat
        layer_alpha = 0.85
        if curr_layer.color_rgba is not None:
            r, g, b, a = curr_layer.color_rgba
            h_from_json, s_from_json, _l = rgb_to_hsl(r, g, b)
            layer_hue = h_from_json
            layer_sat = max(0.25, s_from_json)
            layer_alpha = clamp01(a)

        band_t = band_index / max(1, len(shifted_growth_layers) - 1)
        band_seed = seed + band_index * 173
        for i in range(sample_count):
            i_next = (i + 1) % sample_count
            quad = [prev_resampled[i], prev_resampled[i_next], curr_resampled[i_next], curr_resampled[i]]
            section_idx = i // section_size

            # Section-level "crystal type" profile.
            section_noise = deterministic_noise(section_idx + band_index * 19, band_seed)
            section_hue_shift = (section_noise - 0.5) * 40.0
            section_sat_mul = 0.80 + deterministic_noise(section_idx + 31, band_seed) * 0.55
            section_light_mul = 0.85 + deterministic_noise(section_idx + 67, band_seed) * 0.50
            section_contrast = 0.08 + deterministic_noise(section_idx + 97, band_seed) * 0.12
            section_seam_interval = 4 + int(math.floor(deterministic_noise(section_idx + 41, band_seed) * 4.0))

            # Thick mineral chunk shading per accretion band.
            base_light = 0.28 + 0.36 * band_t
            chunk_jitter = (deterministic_noise(i + band_index * 101, seed) - 0.5) * 0.14
            radial_bias = 0.04 if (i % 2 == 0) else -0.02
            seam_bias = section_contrast if (i % section_seam_interval == 0) else 0.0
            # Intercolor breakup: occasional secondary hue in the same family neighborhood.
            breakup_noise = deterministic_noise(i + section_idx * 131, band_seed)
            breakup_hue_shift = 0.0
            breakup_sat_mul = 1.0
            breakup_light_bias = 0.0
            if breakup_noise > 0.78:
                breakup_hue_shift = 18.0 + deterministic_noise(i + 211, band_seed) * 22.0
                breakup_sat_mul = 0.82
                breakup_light_bias = -0.04
            elif breakup_noise < 0.18:
                breakup_hue_shift = -20.0 - deterministic_noise(i + 223, band_seed) * 18.0
                breakup_sat_mul = 1.10
                breakup_light_bias = 0.05

            lightness = clamp01(
                (base_light + chunk_jitter + radial_bias + seam_bias + breakup_light_bias) * section_light_mul
            )
            base_hue = wrap_hue(layer_hue + section_hue_shift + breakup_hue_shift)
            base_sat = clamp01(layer_sat * section_sat_mul * breakup_sat_mul)

            # Deterministic uneven secondary radial boundary inside each chunk.
            t0 = clamp01(
                0.50
                + (deterministic_noise(i + section_idx * 173, band_seed) - 0.5) * 0.28
                + (deterministic_noise(i + band_index * 257, seed) - 0.5) * 0.12
            )
            t1 = clamp01(
                0.50
                + (deterministic_noise(i_next + section_idx * 173, band_seed) - 0.5) * 0.28
                + (deterministic_noise(i_next + band_index * 257, seed) - 0.5) * 0.12
            )
            p0 = prev_resampled[i]
            p1 = prev_resampled[i_next]
            c0 = curr_resampled[i]
            c1 = curr_resampled[i_next]
            b0 = p0 + (c0 - p0) * t0
            b1 = p1 + (c1 - p1) * t1

            # Inside boundary is lighter; outside boundary is darker.
            inner_fill = hsl_to_hex(base_hue, base_sat, clamp01(lightness + 0.10))
            outer_fill = hsl_to_hex(base_hue, clamp01(base_sat * 0.96), clamp01(lightness - 0.08))

            inner_poly = [p0, p1, b1, b0]
            outer_poly = [b0, b1, c1, c0]

            chunks.append(svg_polygon(outer_poly, outer_fill, "#eef5ff", 0.75, fill_opacity=layer_alpha))
            chunks.append(svg_polygon(inner_poly, inner_fill, "#eef5ff", 0.75, fill_opacity=layer_alpha))

            fill = hsl_to_hex(
                wrap_hue(layer_hue + section_hue_shift + breakup_hue_shift),
                clamp01(layer_sat * section_sat_mul * breakup_sat_mul),
                lightness,
            )
            # subtle center split line to emphasize the secondary boundary
            seam_split = hsl_to_hex(base_hue, clamp01(base_sat * 0.45), clamp01(lightness + 0.04))
            seam_lines.append(
                f'<line x1="{b0.x:.2f}" y1="{b0.y:.2f}" x2="{b1.x:.2f}" y2="{b1.y:.2f}" '
                f'stroke="{seam_split}" stroke-width="0.9" stroke-opacity="{layer_alpha:.3f}" />'
            )

            if i % section_seam_interval == 0:
                a = curr_resampled[i]
                b = prev_resampled[i]
                seam_color = hsl_to_hex(
                    wrap_hue(layer_hue + section_hue_shift * 0.5),
                    clamp01(layer_sat * 0.45),
                    clamp01(lightness + 0.10),
                )
                seam_lines.append(
                    f'<line x1="{a.x:.2f}" y1="{a.y:.2f}" x2="{b.x:.2f}" y2="{b.y:.2f}" '
                    f'stroke="{seam_color}" stroke-width="1.2" stroke-opacity="{layer_alpha:.3f}" />'
                )

        chunks.append(svg_polygon(curr_layer.points, "none", "#eaf3ff", 1.2))

    # Draw newest bands first so earlier growth remains visible on top.
    return defs, list(reversed(chunks)) + list(reversed(seam_lines))


def triangle_centroid(tri: list[Vec2]) -> Vec2:
    return Vec2((tri[0].x + tri[1].x + tri[2].x) / 3.0, (tri[0].y + tri[1].y + tri[2].y) / 3.0)


def triangle_face_normal_2d(tri: list[Vec2], reference_center: Vec2) -> Vec2:
    # Use a pseudo face normal from the longest edge so each triangle reads as a distinct facet.
    edges = [
        tri[1] - tri[0],
        tri[2] - tri[1],
        tri[0] - tri[2],
    ]
    lengths = [e.length() for e in edges]
    longest = edges[lengths.index(max(lengths))]
    n = Vec2(-longest.y, longest.x).normalized()
    centroid = triangle_centroid(tri)
    outward = (centroid - reference_center).normalized()
    if n.x * outward.x + n.y * outward.y < 0.0:
        n = n * -1.0
    return n


def pseudo_lit_triangle_color(
    tri: list[Vec2],
    origin_center: Vec2,
    layer_hue: float,
    layer_sat: float,
    seed: int,
    tri_index: int,
    band_t: float,
) -> str:
    centroid = triangle_centroid(tri)
    to_tri = (centroid - origin_center).normalized()
    normal = triangle_face_normal_2d(tri, origin_center)
    facing = clamp01((normal.x * to_tri.x + normal.y * to_tri.y + 1.0) * 0.5)

    # Add deterministic color breakup around the base hue.
    hue_shift = (deterministic_noise(tri_index + 503, seed) - 0.5) * 34.0
    sat_mul = 0.78 + deterministic_noise(tri_index + 701, seed) * 0.42
    jitter = (deterministic_noise(tri_index + 907, seed) - 0.5) * 0.12
    lightness = clamp01(0.22 + band_t * 0.32 + facing * 0.33 + jitter)

    return hsl_to_hex(
        wrap_hue(layer_hue + hue_shift),
        clamp01(layer_sat * sat_mul),
        lightness,
    )


def render_difference_triangles_layers(
    shifted_growth_layers: list[ShapeLayer],
    fallback_hue: float,
    fallback_sat: float,
    seed: int,
    sample_count: int,
) -> tuple[list[str], list[str]]:
    if len(shifted_growth_layers) <= 1:
        return [], []

    origin_center = polygon_center(shifted_growth_layers[0].points)
    body: list[str] = []
    defs: list[str] = []

    for band_index in range(1, len(shifted_growth_layers)):
        prev_layer = shifted_growth_layers[band_index - 1]
        curr_layer = shifted_growth_layers[band_index]
        prev_resampled = radial_resample(prev_layer.points, origin_center, sample_count)
        curr_resampled = radial_resample(curr_layer.points, origin_center, sample_count)

        layer_hue = fallback_hue
        layer_sat = fallback_sat
        layer_alpha = 0.85
        if curr_layer.color_rgba is not None:
            r, g, b, a = curr_layer.color_rgba
            h_from_json, s_from_json, _l = rgb_to_hsl(r, g, b)
            layer_hue = h_from_json
            layer_sat = max(0.25, s_from_json)
            layer_alpha = clamp01(a)

        band_t = band_index / max(1, len(shifted_growth_layers) - 1)
        band_seed = seed + band_index * 211

        for i in range(sample_count):
            i_next = (i + 1) % sample_count
            p0 = prev_resampled[i]
            p1 = prev_resampled[i_next]
            c0 = curr_resampled[i]
            c1 = curr_resampled[i_next]

            t0 = clamp01(0.36 + deterministic_noise(i + 31, band_seed) * 0.34)
            t1 = clamp01(0.36 + deterministic_noise(i_next + 31, band_seed) * 0.34)
            m0 = p0 + (c0 - p0) * t0
            m1 = p1 + (c1 - p1) * t1

            # Non-radial triangulation: alternating diagonal topology across the strip.
            tris: list[list[Vec2]]
            if (i + band_index) % 2 == 0:
                tris = [
                    [p0, p1, m1],
                    [p0, m1, m0],
                    [m0, m1, c1],
                    [m0, c1, c0],
                ]
            else:
                tris = [
                    [p0, p1, m0],
                    [p1, m1, m0],
                    [m0, m1, c0],
                    [m1, c1, c0],
                ]

            for tri_local_idx, tri in enumerate(tris):
                tri_idx = i * 7 + tri_local_idx + band_index * 997
                fill = pseudo_lit_triangle_color(
                    tri=tri,
                    origin_center=origin_center,
                    layer_hue=layer_hue,
                    layer_sat=layer_sat,
                    seed=band_seed,
                    tri_index=tri_idx,
                    band_t=band_t,
                )
                body.append(svg_polygon(tri, fill, "none", 0.0, fill_opacity=layer_alpha))

    return defs, list(reversed(body))


def write_layered_svg(
    out_path: Path,
    run_id: str,
    layers: list[ShapeLayer],
    hue: float,
    saturation: float,
    seed: int,
    min_facet_lightness: float,
    style: str,
) -> None:
    pad = 40.0
    width, height, _min_x, _min_y, dx, dy = build_canvas(layers, pad)

    # Smaller + older on top:
    # draw bottom->top as reverse of top-priority sort.
    top_priority = sorted(layers, key=lambda s: (s.area, s.index, s.saved_unix))
    draw_order = list(reversed(top_priority))
    growth_order = growth_sorted_layers(layers)

    defs: list[str] = []
    body: list[str] = []

    uses_accretion = style in ["accretion", "plausable_1"]
    uses_difference_triangles = style == "plausable_2"
    style_label = "plausable_1" if uses_accretion else style

    if uses_accretion or uses_difference_triangles:
        shifted_growth_layers: list[ShapeLayer] = []
        for layer in growth_order:
            shifted_growth_layers.append(
                ShapeLayer(
                    index=layer.index,
                    saved_unix=layer.saved_unix,
                    points=translated(layer.points, dx, dy),
                    area=layer.area,
                    color_rgba=layer.color_rgba,
                )
            )
        if uses_difference_triangles:
            tri_defs, tri_body = render_difference_triangles_layers(
                shifted_growth_layers=shifted_growth_layers,
                fallback_hue=hue,
                fallback_sat=saturation,
                seed=seed,
                sample_count=56,
            )
            defs.extend(tri_defs)
            body.extend(tri_body)
        else:
            acc_defs, acc_body = render_accretion_layers(
                shifted_growth_layers=shifted_growth_layers,
                fallback_hue=hue,
                fallback_sat=saturation,
                seed=seed,
                sample_count=56,
            )
            defs.extend(acc_defs)
            body.extend(acc_body)
    else:
        total = max(1, len(draw_order) - 1)
        for layer_idx, layer in enumerate(draw_order):
            shifted = translated(layer.points, dx, dy)
            center = polygon_center(shifted)
            clip_id = f"clip_layer_{layer.index}_{layer_idx}"
            boundary_poly = " ".join(p.to_svg() for p in shifted)
            defs.append(f'<clipPath id="{clip_id}"><polygon points="{boundary_poly}" /></clipPath>')

            layer_depth_01 = layer_idx / total
            layer_hue = hue
            layer_sat = saturation
            layer_alpha = 0.85
            if layer.color_rgba is not None:
                r, g, b, a = layer.color_rgba
                h_from_json, s_from_json, _l_from_json = rgb_to_hsl(r, g, b)
                layer_hue = h_from_json
                layer_sat = max(0.25, s_from_json)
                layer_alpha = clamp01(a)

            base_fill = hsl_to_hex(layer_hue, layer_sat * 0.55, 0.14 + (0.18 * (1.0 - layer_depth_01)))
            body.append(svg_polygon(shifted, base_fill, "#d9e8ff", 1.4, fill_opacity=layer_alpha * 0.9))

            if style == "geode":
                facet_set = build_geode_facets(shifted, seed + layer.index * 97)
            else:
                facet_set = build_gem_facets(shifted, seed + layer.index * 97)

            if facet_set.core_polygon is not None:
                core_fill = hsl_to_hex(layer_hue, clamp01(layer_sat * 0.75), 0.68)
                body.append(
                    svg_polygon(facet_set.core_polygon, core_fill, "#eef6ff", 1.0, fill_opacity=layer_alpha)
                )

            facet_parts: list[str] = []
            for facet_idx, facet in enumerate(facet_set.facets):
                tri, facet_bias = facet
                facet_fill, facet_lightness = facet_color(
                    tri, center, layer_hue, layer_sat, facet_idx, layer_depth_01, facet_bias
                )
                if facet_lightness < min_facet_lightness:
                    continue
                facet_parts.append(
                    svg_polygon(
                        tri,
                        facet_fill,
                        "#e7f0ff",
                        0.7,
                        fill_opacity=layer_alpha,
                    )
                )

            body.append(f'<g clip-path="url(#{clip_id})">{"".join(facet_parts)}</g>')
            body.append(svg_polygon(shifted, "none", "#edf4ff", 1.6))

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">
  <rect width="100%" height="100%" fill="#0a101c" />
  <text x="16" y="22" fill="#9db4de" font-family="monospace" font-size="13">Run: {run_id} | layers: {len(layers)} | style: {style_label} | top priority: smallest + oldest</text>
  <defs>{''.join(defs)}</defs>
  {''.join(body)}
</svg>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding="utf-8")


def write_progressive_plausable_2(
    output_dir: Path,
    run_id: str,
    layers: list[ShapeLayer],
    hue: float,
    saturation: float,
    seed: int,
    min_facet_lightness: float,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    growth_layers = growth_sorted_layers(layers)
    written: list[Path] = []
    for step in range(1, len(growth_layers) + 1):
        partial_layers = growth_layers[:step]
        out_path = output_dir / f"{run_id}_plausable_2_step_{step:02d}.svg"
        write_layered_svg(
            out_path=out_path,
            run_id=run_id,
            layers=partial_layers,
            hue=hue,
            saturation=saturation,
            seed=seed,
            min_facet_lightness=min_facet_lightness,
            style="plausable_2",
        )
        written.append(out_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Render layered gem-faceted shapes from Godot shapes.json")
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to shapes.json or a run_* folder. Defaults to latest run under Godot crystal_shapes.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output/layered_gem.svg"),
        help="Output SVG path.",
    )
    parser.add_argument(
        "--hue",
        type=float,
        default=205.0,
        help="Fallback base hue (0-360) when a shape has no color field.",
    )
    parser.add_argument(
        "--sat",
        type=float,
        default=0.70,
        help="Fallback saturation (0-1) when a shape has no color field.",
    )
    parser.add_argument("--seed", type=int, default=7, help="Deterministic shading seed.")
    parser.add_argument(
        "--min-facet-lightness",
        type=float,
        default=0.0,
        help="Drop triangles darker than this lightness (0-1).",
    )
    parser.add_argument(
        "--style",
        choices=["classic", "geode", "accretion", "plausable_1", "plausable_2"],
        default="plausable_1",
        help="Facet style. plausable_2 uses non-radial difference-triangle band faceting with pseudo lighting.",
    )
    parser.add_argument(
        "--prev-boundary-strength",
        type=float,
        default=0.90,
        help="How strongly to constrain each layer by the previous boundary (0-1).",
    )
    parser.add_argument(
        "--prev-boundary-max-growth",
        type=float,
        default=1.14,
        help="Allowed radial growth ratio vs previous boundary before capping.",
    )
    parser.add_argument(
        "--progressive-output-dir",
        type=Path,
        default=None,
        help="When set with plausable_2, writes one SVG per step as shapes accumulate.",
    )
    args = parser.parse_args()

    json_path = resolve_input_path(args.input)
    run_id, layers = load_shape_layers(json_path)
    if args.style not in ["accretion", "plausable_1", "plausable_2"]:
        layers = stabilize_layers_against_previous(
            layers,
            strength=args.prev_boundary_strength,
            max_growth_ratio=args.prev_boundary_max_growth,
        )
    written_progressive: list[Path] = []
    if args.style == "plausable_2" and args.progressive_output_dir is not None:
        written_progressive = write_progressive_plausable_2(
            output_dir=args.progressive_output_dir,
            run_id=run_id,
            layers=layers,
            hue=args.hue,
            saturation=clamp01(args.sat),
            seed=args.seed,
            min_facet_lightness=clamp01(args.min_facet_lightness),
        )
        # Also write the final frame to --out for consistency.
        write_layered_svg(
            out_path=args.out,
            run_id=run_id,
            layers=layers,
            hue=args.hue,
            saturation=clamp01(args.sat),
            seed=args.seed,
            min_facet_lightness=clamp01(args.min_facet_lightness),
            style=args.style,
        )
    else:
        write_layered_svg(
            out_path=args.out,
            run_id=run_id,
            layers=layers,
            hue=args.hue,
            saturation=clamp01(args.sat),
            seed=args.seed,
            min_facet_lightness=clamp01(args.min_facet_lightness),
            style=args.style,
        )

    top = sorted(layers, key=lambda s: (s.area, s.index, s.saved_unix))
    print(f"Loaded: {json_path}")
    print(f"Run ID: {run_id}")
    print(f"Shapes: {len(layers)}")
    print(f"Top-most layer index: {top[0].index} (smallest/oldest)")
    if args.style in ["accretion", "plausable_1", "plausable_2"]:
        print("Prev-boundary constraint: skipped for accretion style")
    else:
        print(
            "Prev-boundary constraint: "
            f"strength={clamp01(args.prev_boundary_strength):.2f}, "
            f"max_growth={max(1.0, args.prev_boundary_max_growth):.2f}"
        )
    if written_progressive:
        print(f"Progressive frames: {len(written_progressive)}")
        print(f"Progressive dir: {args.progressive_output_dir}")
    print(f"Wrote: {args.out}")


if __name__ == "__main__":
    main()
