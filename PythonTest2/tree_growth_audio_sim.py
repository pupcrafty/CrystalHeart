"""
Audio-driven rectangle tree growth simulation.

Uses the same audio JSONL stream as PythonTest1 (bass/mid/treble),
but maps pulses to three growth channels:
- thickness
- length
- split

Each channel has its own band assignment and threshold.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generator, Iterable, List, Optional, Tuple


@dataclass
class EnergySample:
    bass: float
    mid: float
    treble: float


class EnergyNormalizer:
    def __init__(self, decay: float = 0.995) -> None:
        self.decay = decay
        self.max_bass = 1e-6
        self.max_mid = 1e-6
        self.max_treble = 1e-6

    def normalize(self, sample: EnergySample) -> EnergySample:
        self.max_bass = max(sample.bass, self.max_bass * self.decay)
        self.max_mid = max(sample.mid, self.max_mid * self.decay)
        self.max_treble = max(sample.treble, self.max_treble * self.decay)

        bass = min(1.0, sample.bass / self.max_bass) if self.max_bass > 0 else 0.0
        mid = min(1.0, sample.mid / self.max_mid) if self.max_mid > 0 else 0.0
        treble = min(1.0, sample.treble / self.max_treble) if self.max_treble > 0 else 0.0
        return EnergySample(bass=bass, mid=mid, treble=treble)


class JsonlEnergyStream:
    def __init__(self, path: str, loop: bool = True) -> None:
        self.path = path
        self.loop = loop

    def _iter_file(self) -> Generator[EnergySample, None, None]:
        with open(self.path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if data.get("type") != "audio_payload":
                    continue
                payload = data.get("payload") or {}
                bass = float(payload.get("bass", 0.0))
                mid = float(payload.get("mid", 0.0))
                treble = float(payload.get("treble", 0.0))
                yield EnergySample(bass=bass, mid=mid, treble=treble)

    def stream(self) -> Generator[EnergySample, None, None]:
        while True:
            yielded = False
            for sample in self._iter_file():
                yielded = True
                yield sample
            if not self.loop or not yielded:
                break


class SyntheticEnergyStream:
    def __init__(self, seed: int = 1) -> None:
        self.rand = random.Random(seed)
        self.phase = 0.0

    def stream(self) -> Generator[EnergySample, None, None]:
        while True:
            self.phase += 0.03
            bass = 0.5 + 0.5 * math.sin(self.phase)
            mid = 0.5 + 0.5 * math.sin(self.phase * 0.7 + 1.1)
            treble = 0.5 + 0.5 * math.sin(self.phase * 1.3 + 2.2)
            bass = max(0.0, min(1.0, bass + self.rand.uniform(-0.05, 0.05)))
            mid = max(0.0, min(1.0, mid + self.rand.uniform(-0.05, 0.05)))
            treble = max(0.0, min(1.0, treble + self.rand.uniform(-0.05, 0.05)))
            yield EnergySample(bass=bass, mid=mid, treble=treble)


@dataclass
class TreeNode:
    node_id: int
    parent: Optional[int]
    start: Tuple[float, float]
    direction: Tuple[float, float]
    length: float
    thickness: float
    depth: int
    split_charge: float = 0.0

    def end(self) -> Tuple[float, float]:
        dx, dy = self.direction
        return (self.start[0] + dx * self.length, self.start[1] + dy * self.length)


class RectangleTree:
    def __init__(
        self,
        size: int,
        seed: int = 1,
        split_seed: int = 0,
        root_length: float = 18.0,
        root_thickness: float = 6.0,
        child_length: float = 10.0,
        child_thickness: float = 4.0,
    ) -> None:
        self.size = size
        self.center_x = size / 2.0
        self.rand = random.Random(seed)
        self.split_rand = random.Random(split_seed if split_seed != 0 else seed)
        self.nodes: List[TreeNode] = []
        self.next_id = 1
        self.split_points: List[Tuple[float, float]] = []

        center = (self.center_x, size - 1 - root_thickness / 2.0 - 1.0)
        root = TreeNode(
            node_id=self._new_id(),
            parent=None,
            start=center,
            direction=(0.0, -1.0),
            length=root_length,
            thickness=root_thickness,
            depth=0,
        )
        self.nodes.append(root)

    def _new_id(self) -> int:
        nid = self.next_id
        self.next_id += 1
        return nid

    def _add_child(
        self,
        parent: TreeNode,
        direction: Tuple[float, float],
        length: float,
        thickness: float,
    ) -> Optional[TreeNode]:
        start = parent.end()
        child = TreeNode(
            node_id=self._new_id(),
            parent=parent.node_id,
            start=start,
            direction=direction,
            length=length,
            thickness=thickness,
            depth=parent.depth + 1,
        )
        if not self._fits_in_bounds(child):
            return None
        self.nodes.append(child)
        return child

    def _fits_in_bounds(self, node: TreeNode) -> bool:
        corners = self._tri_vertices(node)
        for x, y in corners:
            if x < 0 or x > self.size - 1 or y < 0 or y > self.size - 1:
                return False
        return True

    def all_nodes(self) -> List[TreeNode]:
        return list(self.nodes)

    def leaves(self) -> List[TreeNode]:
        has_children = set(node.parent for node in self.nodes if node.parent is not None)
        return [node for node in self.nodes if node.node_id not in has_children]

    def root(self) -> Optional[TreeNode]:
        for node in self.nodes:
            if node.parent is None:
                return node
        return None

    def children_of(self, node_id: int) -> List[TreeNode]:
        return [node for node in self.nodes if node.parent == node_id]

    def node_by_id(self, node_id: Optional[int]) -> Optional[TreeNode]:
        if node_id is None:
            return None
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def grow_thickness(self, amount: float, max_thickness: float = 0.0) -> None:
        if amount <= 0:
            return
        nodes = self.nodes
        per_node = amount / max(1, len(nodes))
        for node in nodes:
            node.thickness += per_node
            if max_thickness > 0:
                node.thickness = min(node.thickness, max_thickness)

    def grow_length(self, amount: float, max_length: float = 0.0) -> None:
        if amount <= 0:
            return
        leaves = self.leaves()
        if not leaves:
            return
        per_leaf = amount / len(leaves)
        for leaf in leaves:
            leaf.length += per_leaf
            if max_length > 0:
                leaf.length = min(leaf.length, max_length)
            self._clamp_length_to_bounds(leaf)
        # Parents also grow: 1/4 of the maximum child growth this pulse.
        parent_growth = 0.25 * per_leaf
        if parent_growth > 0:
            has_children = set(node.parent for node in self.nodes if node.parent is not None)
            for node in self.nodes:
                if node.node_id in has_children:
                    node.length += parent_growth
                    if max_length > 0:
                        node.length = min(node.length, max_length)
                    self._clamp_length_to_bounds(node)

    def _clamp_length_to_bounds(self, node: TreeNode) -> None:
        # Binary search for the longest length that keeps the rectangle in bounds.
        lo = 1.0
        hi = max(1.0, node.length)
        for _ in range(18):
            mid = (lo + hi) / 2.0
            test = TreeNode(
                node_id=node.node_id,
                parent=node.parent,
                start=node.start,
                direction=node.direction,
                length=mid,
                thickness=node.thickness,
                depth=node.depth,
                split_charge=node.split_charge,
            )
            if self._fits_in_bounds(test):
                lo = mid
            else:
                hi = mid
        node.length = lo

    def symmetric_leaf(self) -> Optional[TreeNode]:
        leaves = self.leaves()
        if not leaves:
            return None
        # Favor the top-most leaf; tie-breaker on depth.
        leaves.sort(key=lambda leaf: (leaf.end()[1], leaf.depth))
        return leaves[0]

    def mirror_leaf(self, leaf: TreeNode, tolerance: float = 1.0) -> Optional[TreeNode]:
        target_x = 2.0 * self.center_x - leaf.end()[0]
        target_y = leaf.end()[1]
        dx, dy = self._normalize(leaf.direction)
        target_dir = (-dx, dy)
        best = None
        best_dist = float("inf")
        for candidate in self.leaves():
            cdx, cdy = self._normalize(candidate.direction)
            if abs(cdx - target_dir[0]) > 0.2 or abs(cdy - target_dir[1]) > 0.2:
                continue
            ex, ey = candidate.end()
            dist = math.hypot(ex - target_x, ey - target_y)
            if dist < best_dist and dist <= tolerance:
                best = candidate
                best_dist = dist
        return best

    def random_split_candidate(self) -> Optional[TreeNode]:
        if not self.nodes:
            return None
        return self.split_rand.choice(self.nodes)

    def min_split_distance_ok(self, point: Tuple[float, float], min_distance: float) -> bool:
        if min_distance <= 0:
            return True
        for sx, sy in self.split_points:
            if math.hypot(point[0] - sx, point[1] - sy) < min_distance:
                return False
        return True

    def split_direction_candidates(
        self,
        node: TreeNode,
        total_angle_deg: float,
        samples: int,
        min_clearance: float,
        min_split_distance: float,
        overlap_buffer: float,
        child_length: float,
        child_thickness: float,
    ) -> List[Tuple[float, Tuple[float, float]]]:
        span = max(1.0, min(89.0, total_angle_deg))
        half = math.radians(span / 2.0)
        base_angle = math.atan2(node.direction[1], node.direction[0])
        samples = max(3, samples | 1)
        offsets = [
            -half + (2 * half) * i / (samples - 1) for i in range(samples)
        ]
        candidates: List[Tuple[float, Tuple[float, float]]] = []
        for offset in offsets:
            angle = base_angle + offset
            direction = (math.cos(angle), math.sin(angle))
            test = TreeNode(
                node_id=-1,
                parent=node.node_id,
                start=node.end(),
                direction=direction,
                length=child_length,
                thickness=child_thickness,
                depth=node.depth + 1,
            )
            if not self._fits_in_bounds(test):
                continue
            tip = test.end()
            if not self.min_split_distance_ok(tip, min_split_distance):
                continue
            if not self.min_split_distance_ok(node.end(), min_split_distance):
                continue
            if overlap_buffer > 0:
                tminx, tminy, tmaxx, tmaxy = self._tri_aabb(test)
                tminx -= overlap_buffer
                tminy -= overlap_buffer
                tmaxx += overlap_buffer
                tmaxy += overlap_buffer
                overlap = False
                for other in self.nodes:
                    if other.node_id == node.node_id:
                        continue
                    ominx, ominy, omaxx, omaxy = self._tri_aabb(other)
                    if not (tmaxx < ominx or tminx > omaxx or tmaxy < ominy or tminy > omaxy):
                        overlap = True
                        break
                if overlap:
                    continue
            bound_clear = min(
                tip[0],
                tip[1],
                (self.size - 1) - tip[0],
                (self.size - 1) - tip[1],
            )
            split_clear = float("inf")
            for sx, sy in self.split_points:
                split_clear = min(split_clear, math.hypot(tip[0] - sx, tip[1] - sy))
            clearance = min(bound_clear, split_clear if split_clear != float("inf") else bound_clear)
            if clearance < min_clearance:
                continue
            candidates.append((clearance, direction))
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates

    def split_leaf(
        self,
        leaf: TreeNode,
        count: int,
        total_angle_deg: float,
        child_length: float,
        child_thickness: float,
    ) -> int:
        directions = self._split_directions(leaf.direction, count, total_angle_deg)
        created = 0
        for direction in directions:
            child = self._add_child(
                leaf, direction=direction, length=child_length, thickness=child_thickness
            )
            if child is not None:
                created += 1
        if created > 0:
            self.split_points.append(leaf.end())
        return created

    def split_with_directions(
        self,
        leaf: TreeNode,
        directions: List[Tuple[float, float]],
        child_length: float,
        child_thickness: float,
    ) -> int:
        created = 0
        for direction in directions:
            child = self._add_child(
                leaf, direction=direction, length=child_length, thickness=child_thickness
            )
            if child is not None:
                created += 1
        if created > 0:
            self.split_points.append(leaf.end())
        return created

    def _split_directions(
        self, direction: Tuple[float, float], count: int, total_angle_deg: float
    ) -> List[Tuple[float, float]]:
        # Symmetric directions around the parent axis within a total angle < 90 degrees.
        if count <= 1:
            return [self._normalize(direction)]
        span = max(1.0, min(89.0, total_angle_deg))
        half = math.radians(span / 2.0)
        base_angle = math.atan2(direction[1], direction[0])
        if count == 2:
            offsets = [-half, half]
        else:
            offsets = [-half, 0.0, half]
        directions = []
        for offset in offsets[:count]:
            angle = base_angle + offset
            directions.append((math.cos(angle), math.sin(angle)))
        return directions

    def render_rgb(self) -> List[Tuple[int, int, int]]:
        pixels: List[Tuple[int, int, int]] = [(0, 0, 0)] * (self.size * self.size)
        max_depth = max((node.depth for node in self.nodes), default=1)
        for node in self.nodes:
            color = self._color_for_depth(node.depth, max_depth)
            self._draw_rect(pixels, node, color)
        for x, y in self.split_points:
            self._draw_dot(pixels, x, y, radius=2, color=(220, 40, 40))
        return pixels

    def _color_for_depth(self, depth: int, max_depth: int) -> Tuple[int, int, int]:
        t = depth / max(1, max_depth)
        r = int(80 + 140 * t)
        g = int(40 + 160 * (1 - t))
        b = int(120 + 100 * (0.5 + 0.5 * math.sin(t * math.pi)))
        return (r, g, b)

    def _normalize(self, direction: Tuple[float, float]) -> Tuple[float, float]:
        dx, dy = direction
        length = math.hypot(dx, dy)
        if length == 0:
            return (0.0, -1.0)
        return (dx / length, dy / length)

    def _tri_vertices(self, node: TreeNode) -> List[Tuple[float, float]]:
        dx, dy = self._normalize(node.direction)
        px, py = -dy, dx
        half_t = node.thickness / 2.0
        x0, y0 = node.start
        x1, y1 = node.end()
        base_left = (x0 + px * half_t, y0 + py * half_t)
        base_right = (x0 - px * half_t, y0 - py * half_t)
        tip = (x1, y1)
        return [base_left, base_right, tip]

    def _tri_aabb(self, node: TreeNode) -> Tuple[float, float, float, float]:
        verts = self._tri_vertices(node)
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        return (min(xs), min(ys), max(xs), max(ys))

    def _draw_rect(self, pixels: List[Tuple[int, int, int]], node: TreeNode, color) -> None:
        verts = self._tri_vertices(node)
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        ix0 = max(0, int(math.floor(min(xs))))
        ix1 = min(self.size - 1, int(math.ceil(max(xs))))
        iy0 = max(0, int(math.floor(min(ys))))
        iy1 = min(self.size - 1, int(math.ceil(max(ys))))

        (x1, y1), (x2, y2), (x3, y3) = verts
        denom = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if denom == 0:
            return
        for y in range(iy0, iy1 + 1):
            row_offset = y * self.size
            for x in range(ix0, ix1 + 1):
                px0 = x + 0.5
                py0 = y + 0.5
                a = ((y2 - y3) * (px0 - x3) + (x3 - x2) * (py0 - y3)) / denom
                b = ((y3 - y1) * (px0 - x3) + (x1 - x3) * (py0 - y3)) / denom
                c = 1.0 - a - b
                if a >= 0 and b >= 0 and c >= 0:
                    pixels[row_offset + x] = color

    def _draw_dot(
        self, pixels: List[Tuple[int, int, int]], cx: float, cy: float, radius: int, color
    ) -> None:
        ix0 = max(0, int(math.floor(cx - radius)))
        ix1 = min(self.size - 1, int(math.ceil(cx + radius)))
        iy0 = max(0, int(math.floor(cy - radius)))
        iy1 = min(self.size - 1, int(math.ceil(cy + radius)))
        r2 = radius * radius
        for y in range(iy0, iy1 + 1):
            row_offset = y * self.size
            for x in range(ix0, ix1 + 1):
                dx = x + 0.5 - cx
                dy = y + 0.5 - cy
                if dx * dx + dy * dy <= r2:
                    pixels[row_offset + x] = color


def build_energy_stream(source: str, loop: bool, seed: int) -> Iterable[EnergySample]:
    if source == "synthetic":
        return SyntheticEnergyStream(seed=seed).stream()
    if not os.path.exists(source):
        print(f"Energy source not found: {source}. Falling back to synthetic.", file=sys.stderr)
        return SyntheticEnergyStream(seed=seed).stream()
    return JsonlEnergyStream(path=source, loop=loop).stream()


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def band_value(sample: EnergySample, band: str) -> float:
    band = band.lower()
    if band == "bass":
        return sample.bass
    if band == "mid":
        return sample.mid
    if band == "treble":
        return sample.treble
    raise ValueError(f"Unknown band: {band}")


def pulse_amount(value: float, threshold: float, scale: float) -> float:
    if value < threshold:
        return 0.0
    return (value - threshold) * scale


def save_ppm(path: str, size: int, pixels: List[Tuple[int, int, int]]) -> None:
    with open(path, "w", encoding="ascii") as handle:
        handle.write(f"P3\n{size} {size}\n255\n")
        for y in range(size):
            row = pixels[y * size : (y + 1) * size]
            for r, g, b in row:
                handle.write(f"{r} {g} {b} ")
            handle.write("\n")


def save_image(path: str, size: int, pixels: List[Tuple[int, int, int]], fmt: str) -> None:
    fmt = fmt.lower()
    if fmt == "ppm":
        save_ppm(path, size, pixels)
        return
    if fmt != "png":
        raise ValueError(f"Unsupported image format: {fmt}")
    try:
        from PIL import Image  # type: ignore

        img = Image.new("RGB", (size, size))
        img.putdata(pixels)
        img.save(path)
        return
    except Exception:
        pass
    # Fallback to pygame if available.
    try:
        import pygame  # type: ignore

        pygame.init()
        surface = pygame.Surface((size, size))
        surface.lock()
        idx = 0
        for y in range(size):
            for x in range(size):
                surface.set_at((x, y), pixels[idx])
                idx += 1
        surface.unlock()
        pygame.image.save(surface, path)
        pygame.quit()
        return
    except Exception as exc:
        raise RuntimeError(
            "Saving PNG requires Pillow or pygame to be installed."
        ) from exc


def next_image_index(output_dir: str, prefix: str, fmt: str) -> int:
    index = 1
    while True:
        filename = f"{prefix}_{index:04d}.{fmt}"
        path = os.path.join(output_dir, filename)
        if not os.path.exists(path):
            return index
        index += 1


def append_run_log(path: str, config: dict) -> None:
    data: List[dict] = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            data = []
    data.append(config)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def main() -> int:
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument(
        "--config",
        type=str,
        default="tree_config.json",
        help="Path to JSON config file",
    )
    config_args, remaining = config_parser.parse_known_args()
    config = load_config(config_args.config)

    parser = argparse.ArgumentParser(description="Audio-driven rectangle tree growth")
    parser.add_argument("--config", type=str, default=config_args.config, help="Config file")
    parser.add_argument("--size", type=int, default=config.get("size", 200))
    parser.add_argument("--steps", type=int, default=config.get("steps", 900))
    parser.add_argument(
        "--source",
        type=str,
        default=config.get("source", "../Workbook/audio_events.jsonl"),
        help="JSONL audio events file or 'synthetic'",
    )
    parser.add_argument(
        "--no-loop",
        action="store_true",
        default=config.get("no_loop", False),
        help="Do not loop the input stream",
    )
    parser.add_argument("--seed", type=int, default=config.get("seed", 2))
    parser.add_argument(
        "--split-seed",
        type=int,
        default=config.get("split_seed", 0),
        help="Optional seed for split path selection (0 uses --seed)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=config.get("output_dir", "PythonTest2/output"),
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default=config.get("output_prefix", "tree"),
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default=config.get("output_format", "ppm"),
        choices=["ppm", "png"],
    )
    parser.add_argument(
        "--render-every",
        type=int,
        default=config.get("render_every", 0),
        help="Save a frame every N steps (0 saves only final)",
    )
    parser.add_argument(
        "--run-note",
        type=str,
        default=config.get("run_note", ""),
        help="Optional note to store with the run log",
    )
    parser.add_argument(
        "--pygame",
        action="store_true",
        default=config.get("pygame", False),
        help="Display growth live with pygame",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=config.get("scale", 4),
        help="Pixel scale for pygame window",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=config.get("fps", 30),
        help="Frame rate for pygame display",
    )
    parser.add_argument(
        "--steps-per-frame",
        type=int,
        default=config.get("steps_per_frame", 1),
        help="Simulation steps per frame",
    )

    parser.add_argument(
        "--thickness-band",
        type=str,
        default=config.get("thickness_band", "bass"),
    )
    parser.add_argument(
        "--length-band",
        type=str,
        default=config.get("length_band", "mid"),
    )
    parser.add_argument(
        "--split-band",
        type=str,
        default=config.get("split_band", "treble"),
    )
    parser.add_argument(
        "--thickness-threshold",
        type=float,
        default=config.get("thickness_threshold", 0.2),
    )
    parser.add_argument(
        "--length-threshold",
        type=float,
        default=config.get("length_threshold", 0.2),
    )
    parser.add_argument(
        "--split-threshold",
        type=float,
        default=config.get("split_threshold", 0.3),
    )
    parser.add_argument(
        "--thickness-scale",
        type=float,
        default=config.get("thickness_scale", 18.0),
    )
    parser.add_argument(
        "--length-scale",
        type=float,
        default=config.get("length_scale", 24.0),
    )
    parser.add_argument(
        "--split-scale",
        type=float,
        default=config.get("split_scale", 8.0),
    )
    parser.add_argument(
        "--split-total-angle",
        type=float,
        default=config.get("split_total_angle", 80.0),
        help="Total spread angle in degrees for new children (< 90)",
    )
    parser.add_argument(
        "--split-charge-threshold",
        type=float,
        default=config.get("split_charge_threshold", 2.0),
        help="Accumulated split charge required to split",
    )
    parser.add_argument(
        "--split-area-reference",
        type=float,
        default=config.get("split_area_reference", 0.0),
        help="Reference area for split energy scaling (0 uses square_size^2)",
    )
    parser.add_argument(
        "--split-min-distance",
        type=float,
        default=config.get("split_min_distance", 10.0),
        help="Minimum distance from other split points",
    )
    parser.add_argument(
        "--split-min-clearance",
        type=float,
        default=config.get("split_min_clearance", 6.0),
        help="Minimum clearance from bounds/other splits for new branches",
    )
    parser.add_argument(
        "--split-overlap-buffer",
        type=float,
        default=config.get("split_overlap_buffer", 2.0),
        help="Extra padding used to reject overlaps with existing triangles",
    )
    parser.add_argument(
        "--split-angle-samples",
        type=int,
        default=config.get("split_angle_samples", 9),
        help="Number of angle samples to evaluate for split directions",
    )
    parser.add_argument(
        "--max-length",
        type=float,
        default=config.get("max_length", 0.0),
    )
    parser.add_argument(
        "--max-thickness",
        type=float,
        default=config.get("max_thickness", 0.0),
    )

    parser.add_argument(
        "--root-length",
        type=float,
        default=config.get("root_length", 22.0),
    )
    parser.add_argument(
        "--root-thickness",
        type=float,
        default=config.get("root_thickness", 7.0),
    )
    parser.add_argument(
        "--square-size",
        type=float,
        default=config.get("square_size", 6.0),
        help="New rectangles start as N by N squares",
    )
    parser.add_argument(
        "--child-length",
        type=float,
        default=config.get("child_length", 12.0),
    )
    parser.add_argument(
        "--child-thickness",
        type=float,
        default=config.get("child_thickness", 4.0),
    )

    args = parser.parse_args(remaining)

    energy_stream = build_energy_stream(args.source, not args.no_loop, args.seed)
    normalizer = EnergyNormalizer()

    tree = RectangleTree(
        size=args.size,
        seed=args.seed,
        split_seed=args.split_seed,
        root_length=args.root_length,
        root_thickness=args.root_thickness,
        child_length=args.child_length,
        child_thickness=args.child_thickness,
    )
    square_size = max(1.0, args.square_size)
    area_reference = (
        args.split_area_reference if args.split_area_reference > 0 else square_size * square_size
    )
    split_min_distance = max(0.0, args.split_min_distance)
    split_min_clearance = max(0.0, args.split_min_clearance)
    split_overlap_buffer = max(0.0, args.split_overlap_buffer)
    split_angle_samples = max(3, args.split_angle_samples)

    os.makedirs(args.output_dir, exist_ok=True)

    def advance_one_step(step_id: int) -> None:
        nonlocal split_target_id
        raw_energy = next(energy_stream)
        energy = normalizer.normalize(raw_energy)

        thickness_val = band_value(energy, args.thickness_band)
        length_val = band_value(energy, args.length_band)
        split_val = band_value(energy, args.split_band)

        thickness_pulse = pulse_amount(
            thickness_val, args.thickness_threshold, args.thickness_scale
        )
        length_pulse = pulse_amount(length_val, args.length_threshold, args.length_scale)
        split_pulse = pulse_amount(split_val, args.split_threshold, args.split_scale)

        if thickness_pulse > 0:
            tree.grow_thickness(thickness_pulse, max_thickness=args.max_thickness)
        if length_pulse > 0:
            tree.grow_length(length_pulse, max_length=args.max_length)
        if split_pulse > 0:
            leaf = tree.node_by_id(split_target_id)
            if leaf is None:
                leaf = tree.random_split_candidate()
                split_target_id = leaf.node_id if leaf is not None else None
            if leaf is not None:
                leaf.split_charge += split_pulse

                def required_split_charge(node: TreeNode) -> float:
                    area = max(1e-6, 0.5 * node.length * node.thickness)
                    scale = max(1.0, area_reference / area)
                    depth_scale = 2 ** max(0, node.depth)
                    return args.split_charge_threshold * scale * depth_scale

                leaf_required = required_split_charge(leaf)
                if leaf.split_charge >= leaf_required:
                    candidates = tree.split_direction_candidates(
                        leaf,
                        total_angle_deg=args.split_total_angle,
                        samples=split_angle_samples,
                        min_clearance=split_min_clearance,
                        min_split_distance=split_min_distance,
                        overlap_buffer=split_overlap_buffer,
                        child_length=square_size,
                        child_thickness=square_size,
                    )
                    directions: List[Tuple[float, float]] = []
                    if candidates:
                        directions.append(candidates[0][1])
                        if len(candidates) > 1:
                            first_angle = math.atan2(
                                directions[0][1], directions[0][0]
                            )
                            min_sep = math.radians(max(5.0, args.split_total_angle / 4.0))
                            for _, direction in candidates[1:]:
                                angle = math.atan2(direction[1], direction[0])
                                diff = abs((angle - first_angle + math.pi) % (2 * math.pi) - math.pi)
                                if diff >= min_sep:
                                    directions.append(direction)
                                    break
                    if directions:
                        created = tree.split_with_directions(
                            leaf,
                            directions=directions,
                            child_length=square_size,
                            child_thickness=square_size,
                        )
                        if created > 0:
                            leaf.split_charge -= leaf_required * created
                    else:
                        leaf.split_charge = 0.0
                    split_target_id = None

        nonlocal image_index
        if args.render_every > 0 and step_id % args.render_every == 0:
            pixels = tree.render_rgb()
            frame_path = os.path.join(
                args.output_dir, f"{args.output_prefix}_{image_index:04d}.{args.output_format}"
            )
            image_index += 1
            save_image(frame_path, args.size, pixels, args.output_format)
            saved_images.append(frame_path)

    image_index = next_image_index(args.output_dir, args.output_prefix, args.output_format)
    saved_images: List[str] = []

    split_target_id: Optional[int] = None

    if args.pygame:
        try:
            import pygame  # type: ignore
        except Exception as exc:  # pragma: no cover
            print("pygame is required for --pygame mode. Install it and try again.", file=sys.stderr)
            print(f"Import error: {exc}", file=sys.stderr)
            return 1

        pygame.init()
        window_size = args.size * args.scale
        screen = pygame.display.set_mode((window_size, window_size))
        pygame.display.set_caption("Rectangle Tree (Audio Driven)")
        clock = pygame.time.Clock()

        step_id = 0
        running = True
        while running and step_id < args.steps:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            for _ in range(args.steps_per_frame):
                if step_id >= args.steps:
                    break
                step_id += 1
                advance_one_step(step_id)

            pixels = tree.render_rgb()
            surface = pygame.Surface((args.size, args.size))
            surface.lock()
            idx = 0
            for y in range(args.size):
                for x in range(args.size):
                    surface.set_at((x, y), pixels[idx])
                    idx += 1
            surface.unlock()
            scaled = pygame.transform.scale(surface, (window_size, window_size))
            screen.blit(scaled, (0, 0))
            pygame.display.flip()
            clock.tick(args.fps)

        pygame.quit()
    else:
        for step_id in range(1, args.steps + 1):
            advance_one_step(step_id)

    pixels = tree.render_rgb()
    output_path = os.path.join(
        args.output_dir, f"{args.output_prefix}_{image_index:04d}.{args.output_format}"
    )
    image_index += 1
    save_image(output_path, args.size, pixels, args.output_format)
    print(f"Saved: {output_path}")
    saved_images.append(output_path)

    run_config = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output_path": output_path,
        "image_paths": saved_images,
        "args": vars(args),
        "last_instructions": args.run_note,
    }
    log_path = os.path.join(os.path.dirname(__file__), "image_generation_log.json")
    append_run_log(log_path, run_config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
