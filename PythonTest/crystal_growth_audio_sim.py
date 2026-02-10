"""
Crystal growth simulation driven by audio service energies.

Energies:
- A = bass
- B = mid
- C = treble (highs)

Default input uses Workbook/audio_events.jsonl captured from the audio service.
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
    a: float  # bass
    b: float  # mid
    c: float  # treble


MAPPINGS = [
    ("A=bass B=mid C=treble", (0, 1, 2)),
    ("A=bass B=treble C=mid", (0, 2, 1)),
    ("A=mid B=bass C=treble", (1, 0, 2)),
    ("A=mid B=treble C=bass", (1, 2, 0)),
    ("A=treble B=bass C=mid", (2, 0, 1)),
    ("A=treble B=mid C=bass", (2, 1, 0)),
]


class EnergyNormalizer:
    def __init__(self, decay: float = 0.995) -> None:
        self.decay = decay
        self.max_a = 1e-6
        self.max_b = 1e-6
        self.max_c = 1e-6

    def normalize(self, sample: EnergySample) -> EnergySample:
        self.max_a = max(sample.a, self.max_a * self.decay)
        self.max_b = max(sample.b, self.max_b * self.decay)
        self.max_c = max(sample.c, self.max_c * self.decay)

        a = min(1.0, sample.a / self.max_a) if self.max_a > 0 else 0.0
        b = min(1.0, sample.b / self.max_b) if self.max_b > 0 else 0.0
        c = min(1.0, sample.c / self.max_c) if self.max_c > 0 else 0.0
        return EnergySample(a=a, b=b, c=c)


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
                yield EnergySample(a=bass, b=mid, c=treble)

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
            a = 0.5 + 0.5 * math.sin(self.phase)
            b = 0.5 + 0.5 * math.sin(self.phase * 0.7 + 1.1)
            c = 0.5 + 0.5 * math.sin(self.phase * 1.3 + 2.2)
            # add slight noise
            a = max(0.0, min(1.0, a + self.rand.uniform(-0.05, 0.05)))
            b = max(0.0, min(1.0, b + self.rand.uniform(-0.05, 0.05)))
            c = max(0.0, min(1.0, c + self.rand.uniform(-0.05, 0.05)))
            yield EnergySample(a=a, b=b, c=c)


class CrystalGrowth:
    def __init__(self, size: int, seed: int = 1, symmetry_faces: int = 4) -> None:
        self.size = size
        self.rand = random.Random(seed)
        self.grid: List[List[int]] = [[0 for _ in range(size)] for _ in range(size)]
        self.boundary = set()
        self.last_split: Optional[Tuple[int, int]] = None
        self.symmetry_faces = symmetry_faces
        self._seed_center()

    def _seed_center(self) -> None:
        center = self.size // 2
        self.grid[center][center] = 1
        self._add_boundary_neighbors(center, center)

    def _add_boundary_neighbors(self, x: int, y: int) -> None:
        for nx, ny in self._neighbors(x, y):
            if self.grid[ny][nx] == 0:
                self.boundary.add((nx, ny))

    def _neighbors(self, x: int, y: int) -> Iterable[Tuple[int, int]]:
        if x > 0:
            yield x - 1, y
        if x < self.size - 1:
            yield x + 1, y
        if y > 0:
            yield x, y - 1
        if y < self.size - 1:
            yield x, y + 1

    def _neighbor_count(self, x: int, y: int) -> int:
        count = 0
        for nx, ny in self._neighbors(x, y):
            if self.grid[ny][nx] > 0:
                count += 1
        return count

    def _axis_thickness(self, x: int, y: int) -> int:
        # Measure occupied length through (x, y) along 4 axes.
        return max(
            self._line_length(x, y, 1, 0),  # x axis
            self._line_length(x, y, 0, 1),  # y axis
            self._line_length(x, y, 1, 1),  # x = y
            self._line_length(x, y, 1, -1),  # x = -y
        )

    def _perpendicular_thickness(self, x: int, y: int) -> int:
        # Estimate split direction from neighbor vectors, then measure thickness
        # along the perpendicular axis.
        dx, dy = self._split_direction(x, y)
        if dx == 0 and dy == 0:
            # Fallback to max axis thickness when direction is ambiguous.
            return self._axis_thickness(x, y)
        # Perpendicular direction
        pdx, pdy = -dy, dx
        return self._line_length(x, y, pdx, pdy)

    def _split_direction(self, x: int, y: int) -> Tuple[int, int]:
        vx, vy = 0, 0
        for nx, ny in self._neighbors(x, y):
            if self.grid[ny][nx] > 0:
                vx += x - nx
                vy += y - ny
        return self._quantize_dir(vx, vy)

    def _quantize_dir(self, vx: int, vy: int) -> Tuple[int, int]:
        # Snap direction to 8-connected grid.
        if vx == 0 and vy == 0:
            return 0, 0
        ax = abs(vx)
        ay = abs(vy)
        if ax >= 2 * ay:
            return (1 if vx > 0 else -1), 0
        if ay >= 2 * ax:
            return 0, (1 if vy > 0 else -1)
        return (1 if vx > 0 else -1), (1 if vy > 0 else -1)

    def _line_length(self, x: int, y: int, dx: int, dy: int) -> int:
        length = 1  # include the candidate point
        cx, cy = x + dx, y + dy
        while 0 <= cx < self.size and 0 <= cy < self.size and self.grid[cy][cx] > 0:
            length += 1
            cx += dx
            cy += dy
        cx, cy = x - dx, y - dy
        while 0 <= cx < self.size and 0 <= cy < self.size and self.grid[cy][cx] > 0:
            length += 1
            cx -= dx
            cy -= dy
        return length

    def _local_density(self, x: int, y: int, radius: int = 2) -> float:
        # Fraction of occupied cells in a square neighborhood, excluding (x, y).
        total = 0
        occupied = 0
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                nx = x + dx
                ny = y + dy
                if 0 <= nx < self.size and 0 <= ny < self.size:
                    total += 1
                    if self.grid[ny][nx] > 0:
                        occupied += 1
        if total == 0:
            return 0.0
        return occupied / total

    def step(
        self,
        step_id: int,
        energy: EnergySample,
        symmetric: bool = True,
        split_thickness: int = 3,
        outward_weight: float = 0.0,
        seed_boost_start: float = 1.0,
        seed_boost_end: float = 1.0,
        seed_boost_steps: int = 0,
        min_outward_factor: float = 0.0,
        auto_fill_neighbors: int = 0,
        self_repulsion: float = 0.75,
        facet_faces: int = 0,
        facet_strength: float = 0.0,
    ) -> int:
        if not self.boundary:
            return 0

        base_rate = 0.02 + 0.08 * energy.a + 0.05 * energy.b
        max_add = 1 + int(5 * energy.a + 3 * energy.b + 2 * energy.c)
        max_dist = math.sqrt(2) * (self.size - 1)
        cx = self.size // 2
        cy = self.size // 2

        candidates = list(self.boundary)
        self.rand.shuffle(candidates)

        added = 0
        for x, y in candidates:
            neighbors = self._neighbor_count(x, y)
            support = neighbors / 4.0
            noise = (self.rand.random() * 2.0 - 1.0) * energy.c
            # Favor structured, symmetric growth and reduce noise.
            prob = base_rate + 0.4 * support * energy.b + 0.12 * support + 0.02 * noise

            # Favor areas farther from the last split point.
            if self.last_split is not None:
                dx = x - self.last_split[0]
                dy = y - self.last_split[1]
                dist_norm = math.sqrt(dx * dx + dy * dy) / max_dist
                prob += 0.18 * dist_norm

            # Optional outward bias away from center.
            if outward_weight > 0.0:
                odx = x - cx
                ody = y - cy
                out_norm = math.sqrt(odx * odx + ody * ody) / max_dist
                prob += outward_weight * out_norm

            # Facet bias: favor growth aligned with discrete crystal faces.
            if facet_faces >= 2 and facet_strength > 0.0:
                alignment = self._facet_alignment(x, y, cx, cy, facet_faces)
                prob += facet_strength * alignment

            # Repel from dense or self-connecting areas.
            density = self._local_density(x, y, radius=2)
            prob -= self_repulsion * density
            # Scale total probability by outward gradient (center -> 0).
            out_norm = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_dist
            prob *= max(min_outward_factor, out_norm)
            # Apply seeding boost that decays over time.
            if seed_boost_steps > 0:
                t = min(1.0, max(0.0, step_id / seed_boost_steps))
                boost = seed_boost_start + (seed_boost_end - seed_boost_start) * t
            else:
                boost = seed_boost_start
            prob *= max(0.0, boost)
            prob = max(0.0, min(1.0, prob))

            if self.rand.random() < prob:
                # Only allow splits when thickness along key axes is sufficient.
                if not self._allow_split_for_points(x, y, split_thickness, symmetric):
                    # If split is blocked, try to thicken perpendicular to split direction.
                    added += self._thicken_instead_of_split(
                        x, y, step_id, symmetric=symmetric
                    )
                    if added >= max_add:
                        break
                    continue
                # Update last split when we branch (more than one neighbor).
                if neighbors >= 2:
                    self.last_split = (x, y)
                added += self._add_cell(x, y, step_id, symmetric=symmetric)
                if added >= max_add:
                    break

        if auto_fill_neighbors > 0:
            added += self._auto_fill(auto_fill_neighbors, step_id, symmetric=symmetric)

        return added

    def _facet_alignment(self, x: int, y: int, cx: int, cy: int, faces: int) -> float:
        dx = x - cx
        dy = y - cy
        if dx == 0 and dy == 0:
            return 0.0
        length = math.sqrt(dx * dx + dy * dy)
        vx = dx / length
        vy = dy / length
        best = 0.0
        for k in range(faces):
            angle = (2.0 * math.pi * k) / faces
            fx = math.cos(angle)
            fy = math.sin(angle)
            dot = vx * fx + vy * fy
            if dot > best:
                best = dot
        # Normalize to 0..1 range
        return max(0.0, best)

    def _add_cell(self, x: int, y: int, step_id: int, symmetric: bool) -> int:
        if symmetric:
            points = self._symmetric_points(x, y)
        else:
            points = {(x, y)}

        added = 0
        for px, py in points:
            if 0 <= px < self.size and 0 <= py < self.size and self.grid[py][px] == 0:
                self.grid[py][px] = step_id
                if (px, py) in self.boundary:
                    self.boundary.remove((px, py))
                self._add_boundary_neighbors(px, py)
                added += 1
        return added

    def _allow_split_for_points(
        self, x: int, y: int, split_thickness: int, symmetric: bool
    ) -> bool:
        if split_thickness <= 0:
            return True
        points = self._symmetric_points(x, y) if symmetric else {(x, y)}
        for px, py in points:
            if not (0 <= px < self.size and 0 <= py < self.size):
                continue
            if self.grid[py][px] != 0:
                continue
            neighbors = self._neighbor_count(px, py)
            if neighbors >= 2:
                thickness = self._perpendicular_thickness(px, py)
                if thickness < split_thickness:
                    return False
        return True

    def _auto_fill(self, threshold: int, step_id: int, symmetric: bool) -> int:
        if threshold <= 0:
            return 0
        added = 0
        changed = True
        while changed:
            changed = False
            for x, y in list(self.boundary):
                if self.grid[y][x] != 0:
                    continue
                if self._neighbor_count(x, y) >= threshold:
                    added += self._add_cell(x, y, step_id, symmetric=symmetric)
                    changed = True
        return added

    def _thicken_instead_of_split(
        self, x: int, y: int, step_id: int, symmetric: bool
    ) -> int:
        dx, dy = self._split_direction(x, y)
        if dx == 0 and dy == 0:
            return 0
        pdx, pdy = -dy, dx
        candidates = [(x + pdx, y + pdy), (x - pdx, y - pdy)]
        added = 0
        for tx, ty in candidates:
            if 0 <= tx < self.size and 0 <= ty < self.size and self.grid[ty][tx] == 0:
                added += self._add_cell(tx, ty, step_id, symmetric=symmetric)
                break
        return added

    def _symmetric_points(self, x: int, y: int) -> set[Tuple[int, int]]:
        faces = max(1, self.symmetry_faces)
        if faces == 1:
            return {(x, y)}

        cx = self.size // 2
        cy = self.size // 2
        dx = x - cx
        dy = y - cy

        points: set[Tuple[int, int]] = set()
        for k in range(faces):
            angle = (2.0 * math.pi * k) / faces
            rx = dx * math.cos(angle) - dy * math.sin(angle)
            ry = dx * math.sin(angle) + dy * math.cos(angle)
            px = int(round(cx + rx))
            py = int(round(cy + ry))
            points.add((px, py))
        return points


    def render_ascii(self) -> str:
        lines = []
        for row in self.grid:
            lines.append("".join("#" if v > 0 else "." for v in row))
        return "\n".join(lines)

    def save_ppm(self, path: str) -> None:
        max_step = max(max(row) for row in self.grid)
        if max_step == 0:
            max_step = 1

        with open(path, "w", encoding="ascii") as handle:
            handle.write(f"P3\n{self.size} {self.size}\n255\n")
            for row in self.grid:
                for value in row:
                    if value == 0:
                        handle.write("0 0 0 ")
                    else:
                        t = value / max_step
                        r = int(80 + 175 * t)
                        g = int(40 + 120 * (1 - t))
                        b = int(100 + 155 * (0.5 + 0.5 * math.sin(t * math.pi)))
                        handle.write(f"{r} {g} {b} ")
                handle.write("\n")

    def save_image(self, path: str, fmt: str) -> None:
        fmt = fmt.lower()
        if fmt == "ppm":
            self.save_ppm(path)
            return

        if fmt != "png":
            raise ValueError(f"Unsupported image format: {fmt}")

        pixels = self.to_rgb_pixels()
        size = self.size
        # Try Pillow first.
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
            _blit_pixels(surface, pixels, size)
            pygame.image.save(surface, path)
            pygame.quit()
            return
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Saving PNG requires Pillow or pygame to be installed."
            ) from exc

    def to_rgb_pixels(self) -> List[Tuple[int, int, int]]:
        max_step = max(max(row) for row in self.grid)
        if max_step == 0:
            max_step = 1
        pixels: List[Tuple[int, int, int]] = []
        for row in self.grid:
            for value in row:
                if value == 0:
                    pixels.append((0, 0, 0))
                else:
                    t = value / max_step
                    r = int(80 + 175 * t)
                    g = int(40 + 120 * (1 - t))
                    b = int(100 + 155 * (0.5 + 0.5 * math.sin(t * math.pi)))
                    pixels.append((r, g, b))
        return pixels


def build_energy_stream(source: str, loop: bool, seed: int) -> Iterable[EnergySample]:
    if source == "synthetic":
        return SyntheticEnergyStream(seed=seed).stream()

    if not os.path.exists(source):
        print(f"Energy source not found: {source}. Falling back to synthetic.", file=sys.stderr)
        return SyntheticEnergyStream(seed=seed).stream()

    return JsonlEnergyStream(path=source, loop=loop).stream()


def apply_mapping(sample: EnergySample, mapping_index: int) -> Tuple[EnergySample, str]:
    label, order = MAPPINGS[mapping_index % len(MAPPINGS)]
    values = [sample.a, sample.b, sample.c]
    mapped = EnergySample(a=values[order[0]], b=values[order[1]], c=values[order[2]])
    return mapped, label


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument(
        "--config",
        type=str,
        default="crystal_config.json",
        help="Path to JSON config file",
    )
    config_args, remaining = config_parser.parse_known_args()
    config = load_config(config_args.config)

    parser = argparse.ArgumentParser(description="Audio-driven crystal growth simulation")
    parser.add_argument("--config", type=str, default=config_args.config, help="Config file")
    parser.add_argument("--size", type=int, default=config.get("size", 60), help="Grid size (NxN)")
    parser.add_argument(
        "--steps", type=int, default=config.get("steps", 500), help="Number of growth steps"
    )
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
    parser.add_argument("--seed", type=int, default=config.get("seed", 1), help="Random seed")
    parser.add_argument(
        "--render-every",
        type=int,
        default=config.get("render_every", 0),
        help="Print ASCII every N steps",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=config.get("output_dir", "."),
        help="Directory for output images",
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default=config.get("output_prefix", "crystal"),
        help="Output filename prefix",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default=config.get("output_format", "ppm"),
        choices=["ppm", "png"],
        help="Output image format",
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
        default=config.get("scale", 8),
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
        "--no-symmetry",
        action="store_true",
        default=config.get("no_symmetry", False),
        help="Disable mirrored growth symmetry",
    )
    parser.add_argument(
        "--symmetry-faces",
        type=int,
        default=config.get("symmetry_faces", 4),
        help="Number of symmetry faces (2-20). Use --no-symmetry for 1.",
    )
    parser.add_argument(
        "--steps-per-mapping",
        type=int,
        default=config.get("steps_per_mapping", 200),
        help="Steps to run before switching to the next A/B/C mapping",
    )
    parser.add_argument(
        "--mapping-start",
        type=int,
        default=config.get("mapping_start", 1),
        help="Start at this mapping index (0-based). Default 1 means next mapping.",
    )
    parser.add_argument(
        "--threshold-a",
        type=float,
        default=config.get("threshold_a", 0.0),
        help="Minimum A energy required for growth",
    )
    parser.add_argument(
        "--threshold-b",
        type=float,
        default=config.get("threshold_b", 0.0),
        help="Minimum B energy required for growth",
    )
    parser.add_argument(
        "--threshold-c",
        type=float,
        default=config.get("threshold_c", 0.0),
        help="Minimum C energy required for growth",
    )
    parser.add_argument(
        "--split-thickness",
        type=int,
        default=config.get("split_thickness", 3),
        help="Minimum thickness along key axes required for splits",
    )
    parser.add_argument(
        "--outward-weight",
        type=float,
        default=config.get("outward_weight", 0.0),
        help="Bias growth away from center (0.0 to ~0.5)",
    )
    parser.add_argument(
        "--min-outward-factor",
        type=float,
        default=config.get("min_outward_factor", 0.15),
        help="Minimum outward gradient factor (0.0 to 1.0)",
    )
    parser.add_argument(
        "--auto-fill-neighbors",
        type=int,
        default=config.get("auto_fill_neighbors", 0),
        help="Auto-fill any cell with at least N neighbors (0 disables)",
    )
    parser.add_argument(
        "--self-repulsion",
        type=float,
        default=config.get("self_repulsion", 1.2),
        help="Strength of repulsion from dense areas",
    )
    parser.add_argument(
        "--facet-faces",
        type=int,
        default=config.get("facet_faces", 6),
        help="Number of facet directions to favor (0 disables)",
    )
    parser.add_argument(
        "--facet-strength",
        type=float,
        default=config.get("facet_strength", 0.35),
        help="Strength of facet alignment bias",
    )
    parser.add_argument(
        "--seed-boost-start",
        type=float,
        default=config.get("seed_boost_start", 2.5),
        help="Initial multiplier for growth probability",
    )
    parser.add_argument(
        "--seed-boost-end",
        type=float,
        default=config.get("seed_boost_end", 1.0),
        help="Final multiplier after boost decay",
    )
    parser.add_argument(
        "--seed-boost-steps",
        type=int,
        default=config.get("seed_boost_steps", 200),
        help="Steps to decay seed boost over (0 disables)",
    )

    args = parser.parse_args(remaining)

    energy_stream = build_energy_stream(args.source, not args.no_loop, args.seed)
    normalizer = EnergyNormalizer()

    symmetry_faces = 1 if args.no_symmetry else max(2, min(20, args.symmetry_faces))
    sim = CrystalGrowth(size=args.size, seed=args.seed, symmetry_faces=symmetry_faces)

    os.makedirs(args.output_dir, exist_ok=True)
    output_path, run_index = next_output_path(
        args.output_dir, args.output_prefix, args.output_format
    )

    if args.pygame:
        try:
            import pygame  # type: ignore
        except Exception as exc:  # pragma: no cover - pygame optional
            print("pygame is required for --pygame mode. Install it and try again.", file=sys.stderr)
            print(f"Import error: {exc}", file=sys.stderr)
            return 1

        pygame.init()
        window_size = args.size * args.scale
        screen = pygame.display.set_mode((window_size, window_size))
        pygame.display.set_caption("Crystal Growth (Audio Driven)")
        clock = pygame.time.Clock()

        step_id = 0
        current_mapping = -1
        running = True
        while running and step_id < args.steps:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            for _ in range(args.steps_per_frame):
                if step_id >= args.steps:
                    break
                step_id += 1
                raw_energy = next(energy_stream)
                energy = normalizer.normalize(raw_energy)
                mapping_index = (step_id - 1) // max(1, args.steps_per_mapping)
                mapping_index += args.mapping_start
                energy, mapping_label = apply_mapping(energy, mapping_index)
                if (
                    energy.a < args.threshold_a
                    or energy.b < args.threshold_b
                    or energy.c < args.threshold_c
                ):
                    continue
                if mapping_index != current_mapping:
                    current_mapping = mapping_index
                    pygame.display.set_caption(f"Crystal Growth (Audio Driven) | {mapping_label}")
                sim.step(
                    step_id,
                    energy,
                    symmetric=not args.no_symmetry,
                    split_thickness=args.split_thickness,
                    outward_weight=args.outward_weight,
                    seed_boost_start=args.seed_boost_start,
                    seed_boost_end=args.seed_boost_end,
                    seed_boost_steps=args.seed_boost_steps,
                    min_outward_factor=args.min_outward_factor,
                    auto_fill_neighbors=args.auto_fill_neighbors,
                    self_repulsion=args.self_repulsion,
                    facet_faces=args.facet_faces,
                    facet_strength=args.facet_strength,
                )

            pixels = sim.to_rgb_pixels()
            surface = pygame.Surface((args.size, args.size))
            _blit_pixels(surface, pixels, args.size)
            scaled = pygame.transform.scale(surface, (window_size, window_size))
            screen.blit(scaled, (0, 0))
            pygame.display.flip()
            clock.tick(args.fps)

        pygame.quit()
    else:
        current_mapping = -1
        for step_id in range(1, args.steps + 1):
            raw_energy = next(energy_stream)
            energy = normalizer.normalize(raw_energy)
            mapping_index = (step_id - 1) // max(1, args.steps_per_mapping)
            mapping_index += args.mapping_start
            energy, mapping_label = apply_mapping(energy, mapping_index)
            if (
                energy.a < args.threshold_a
                or energy.b < args.threshold_b
                or energy.c < args.threshold_c
            ):
                continue
            if mapping_index != current_mapping:
                current_mapping = mapping_index
                print(f"\nMapping: {mapping_label}")
            sim.step(
                step_id,
                energy,
                symmetric=not args.no_symmetry,
                split_thickness=args.split_thickness,
                outward_weight=args.outward_weight,
                seed_boost_start=args.seed_boost_start,
                seed_boost_end=args.seed_boost_end,
                seed_boost_steps=args.seed_boost_steps,
                min_outward_factor=args.min_outward_factor,
                auto_fill_neighbors=args.auto_fill_neighbors,
                self_repulsion=args.self_repulsion,
                facet_faces=args.facet_faces,
                facet_strength=args.facet_strength,
            )

            if args.render_every > 0 and step_id % args.render_every == 0:
                print(
                    f"\nStep {step_id} | A(bass)={energy.a:.2f} "
                    f"B(mid)={energy.b:.2f} C(treble)={energy.c:.2f}"
                )
                print(sim.render_ascii())

    sim.save_image(output_path, args.output_format)
    print(f"Saved: {output_path}")

    run_config = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output_path": output_path,
        "run_index": run_index,
        "args": vars(args),
        "symmetry_faces": symmetry_faces,
        "mapping_start": args.mapping_start,
        "mapping_steps": args.steps_per_mapping,
        "mapping_labels": [label for (label, _) in MAPPINGS],
    }
    log_path = os.path.join(os.path.dirname(__file__), "image_generation_log.json")
    last_config = append_run_log(log_path, run_config)
    change_log_path = os.path.join(
        os.path.dirname(__file__), "..", "Workbook", "image_generation_changes.jsonl"
    )
    append_change_log(change_log_path, last_config, run_config)
    return 0


def _blit_pixels(surface, pixels: List[Tuple[int, int, int]], size: int) -> None:
    # Set pixels without numpy to keep dependencies minimal.
    surface.lock()
    idx = 0
    for y in range(size):
        for x in range(size):
            surface.set_at((x, y), pixels[idx])
            idx += 1
    surface.unlock()


def next_output_path(output_dir: str, prefix: str, fmt: str) -> Tuple[str, int]:
    index = 1
    while True:
        filename = f"{prefix}_{index:04d}.{fmt}"
        path = os.path.join(output_dir, filename)
        if not os.path.exists(path):
            return path, index
        index += 1


def append_run_log(path: str, config: dict) -> Optional[dict]:
    data: List[dict] = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            data = []
    last_config = data[-1] if data else None
    data.append(config)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    return last_config


def append_change_log(path: str, last_config: Optional[dict], new_config: dict) -> None:
    changes: List[str] = []
    if last_config is None:
        changes.append("initial run")
    else:
        last_args = last_config.get("args", {})
        new_args = new_config.get("args", {})
        for key in sorted(set(last_args.keys()) | set(new_args.keys())):
            if last_args.get(key) != new_args.get(key):
                changes.append(
                    f"arg '{key}' changed from {last_args.get(key)} to {new_args.get(key)}"
                )
        if last_config.get("symmetry_faces") != new_config.get("symmetry_faces"):
            changes.append(
                f"symmetry_faces changed from {last_config.get('symmetry_faces')} "
                f"to {new_config.get('symmetry_faces')}"
            )
        if last_config.get("mapping_start") != new_config.get("mapping_start"):
            changes.append(
                f"mapping_start changed from {last_config.get('mapping_start')} "
                f"to {new_config.get('mapping_start')}"
            )
        if last_config.get("mapping_steps") != new_config.get("mapping_steps"):
            changes.append(
                f"steps_per_mapping changed from {last_config.get('mapping_steps')} "
                f"to {new_config.get('mapping_steps')}"
            )

    entry = {
        "timestamp": new_config["timestamp"],
        "output_path": new_config["output_path"],
        "run_index": new_config["run_index"],
        "changes": changes,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
