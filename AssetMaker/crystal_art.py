import math
import os
import random
import re
import sys
import time

import pygame

WIDTH = 900
HEIGHT = 900
BG_COLOR = (12, 14, 18)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def next_index(prefix):
    pattern = re.compile(rf"^{re.escape(prefix)}_(\\d+)\\.png$")
    max_idx = -1
    for name in os.listdir(OUTPUT_DIR):
        m = pattern.match(name)
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    return max_idx + 1


def save_frame(screen, prefix):
    ensure_output_dir()
    idx = next_index(prefix)
    path = os.path.join(OUTPUT_DIR, f"{prefix}_{idx:04d}.png")
    pygame.image.save(screen, path)
    return path


def fade(t):
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def hash_noise(ix, iy):
    n = ix * 374761393 + iy * 668265263
    n = (n ^ (n >> 13)) * 1274126177
    n = n ^ (n >> 16)
    return (n & 0xFFFFFFFF) / 0xFFFFFFFF


def value_noise(x, y):
    x0 = math.floor(x)
    y0 = math.floor(y)
    x1 = x0 + 1
    y1 = y0 + 1

    sx = fade(x - x0)
    sy = fade(y - y0)

    n0 = hash_noise(x0, y0)
    n1 = hash_noise(x1, y0)
    ix0 = lerp(n0, n1, sx)

    n0 = hash_noise(x0, y1)
    n1 = hash_noise(x1, y1)
    ix1 = lerp(n0, n1, sx)

    return lerp(ix0, ix1, sy)


def rect_corners(center, direction, length, width):
    cx, cy = center
    dx, dy = direction
    half_l = length * 0.5
    half_w = width * 0.5
    px, py = -dy, dx

    lx, ly = dx * half_l, dy * half_l
    wx, wy = px * half_w, py * half_w

    return [
        (cx - lx - wx, cy - ly - wy),
        (cx + lx - wx, cy + ly - wy),
        (cx + lx + wx, cy + ly + wy),
        (cx - lx + wx, cy - ly + wy),
    ]


def draw_oriented_rect(surface, center, direction, length, width, color, alpha=255):
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pts = rect_corners(center, direction, length, width)
    pygame.draw.polygon(layer, (*color, alpha), pts)
    surface.blit(layer, (0, 0))


def handle_events():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.quit()
            raise SystemExit


def render_base(screen):
    screen.fill(BG_COLOR)


# 1) Stamped prisms along a noisy field

def draw_stamped_prisms(screen, clock):
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    base_length = 120
    base_width = 14
    len_jitter = 0.35
    wid_jitter = 0.35
    angle_jitter = 0.25
    freq = 0.008
    seeds = 900

    for i in range(seeds):
        handle_events()
        x = random.uniform(0, WIDTH)
        y = random.uniform(0, HEIGHT)
        angle = value_noise(x * freq, y * freq) * math.tau
        angle += random.uniform(-angle_jitter, angle_jitter)
        length = max(20.0, base_length * (1.0 + random.gauss(0, len_jitter)))
        width = max(4.0, base_width * (1.0 + random.gauss(0, wid_jitter)))
        dx, dy = math.cos(angle), math.sin(angle)
        color = (120, 180, 210)
        draw_oriented_rect(layer, (x, y), (dx, dy), length, width, color, alpha=160)

        if i % 12 == 0:
            render_base(screen)
            screen.blit(layer, (0, 0))
            pygame.display.flip()
            clock.tick(60)

    render_base(screen)
    screen.blit(layer, (0, 0))
    pygame.display.flip()


# 2) Seed-and-grow rods

def rect_axes(direction):
    dx, dy = direction
    return [(dx, dy), (-dy, dx)]


def project(points, axis):
    ax, ay = axis
    dots = [p[0] * ax + p[1] * ay for p in points]
    return min(dots), max(dots)


def rects_intersect(a, b):
    a_pts = rect_corners(a["center"], a["dir"], a["length"], a["width"])
    b_pts = rect_corners(b["center"], b["dir"], b["length"], b["width"])

    axes = rect_axes(a["dir"]) + rect_axes(b["dir"])
    for axis in axes:
        a_min, a_max = project(a_pts, axis)
        b_min, b_max = project(b_pts, axis)
        if a_max < b_min or b_max < a_min:
            return False
    return True


def rect_in_bounds(rect):
    pts = rect_corners(rect["center"], rect["dir"], rect["length"], rect["width"])
    for x, y in pts:
        if x < 0 or x > WIDTH or y < 0 or y > HEIGHT:
            return False
    return True


def draw_growing_rods(screen, clock):
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    rods = []
    rod_count = 45
    max_rods = 90

    for _ in range(rod_count):
        angle = random.uniform(0, math.tau)
        rods.append(
            {
                "center": (random.uniform(80, WIDTH - 80), random.uniform(80, HEIGHT - 80)),
                "dir": (math.cos(angle), math.sin(angle)),
                "length": random.uniform(30, 60),
                "width": random.uniform(6, 10),
                "energy": random.uniform(0.6, 1.2),
                "active": True,
            }
        )

    ticks = 520
    for t in range(ticks):
        handle_events()

        for rod in rods:
            if not rod["active"]:
                continue
            if random.random() > rod["energy"]:
                continue

            base_len = 1.8
            base_wid = 0.08
            grow_len = base_len * (1.0 + value_noise(rod["center"][0] * 0.01, rod["center"][1] * 0.01))
            grow_wid = base_wid

            # Attempt length growth
            test = dict(rod)
            test["length"] = rod["length"] + grow_len
            if rect_in_bounds(test):
                collided = any(test is not other and rects_intersect(test, other) for other in rods if other is not rod)
                if not collided:
                    rod["length"] = test["length"]
                else:
                    rod["active"] = False

            # Width growth is gentler
            test = dict(rod)
            test["width"] = rod["width"] + grow_wid
            if rect_in_bounds(test):
                collided = any(test is not other and rects_intersect(test, other) for other in rods if other is not rod)
                if not collided:
                    rod["width"] = test["width"]

            # Rare branching
            if rod["active"] and len(rods) < max_rods and random.random() < 0.01:
                angle = math.atan2(rod["dir"][1], rod["dir"][0])
                offset = random.choice([-1, 1]) * random.uniform(0.25, 0.45)
                na = angle + offset
                rods.append(
                    {
                        "center": rod["center"],
                        "dir": (math.cos(na), math.sin(na)),
                        "length": rod["length"] * 0.5,
                        "width": rod["width"] * 0.6,
                        "energy": rod["energy"] * 0.9,
                        "active": True,
                    }
                )

        layer.fill((0, 0, 0, 0))
        for rod in rods:
            color = (150, 210, 220)
            draw_oriented_rect(layer, rod["center"], rod["dir"], rod["length"], rod["width"], color, alpha=190)

        if t % 4 == 0:
            render_base(screen)
            screen.blit(layer, (0, 0))
            pygame.display.flip()
            clock.tick(60)

    render_base(screen)
    screen.blit(layer, (0, 0))
    pygame.display.flip()


# 3) Rectangular diffusion-limited aggregation

def draw_rect_dla(screen, clock):
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    cell = 4
    gw = WIDTH // cell
    gh = HEIGHT // cell

    occupied = set()
    center = (gw // 2, gh // 2)
    occupied.add(center)

    def neighbors(x, y):
        return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]

    def is_adjacent(x, y):
        return any((nx, ny) in occupied for nx, ny in neighbors(x, y))

    def draw_cell(x, y):
        rect = pygame.Rect(x * cell, y * cell, cell, cell)
        pygame.draw.rect(layer, (160, 220, 230, 220), rect)

    draw_cell(*center)

    walkers = 2800
    max_steps = 2000
    bias = 0.65
    for i in range(walkers):
        handle_events()

        x = random.randint(0, gw - 1)
        y = random.choice([0, gh - 1]) if random.random() < 0.5 else random.randint(0, gh - 1)

        for _ in range(max_steps):
            if is_adjacent(x, y):
                occupied.add((x, y))
                draw_cell(x, y)
                break

            r = random.random()
            if r < bias:
                if random.random() < 0.5:
                    x += random.choice([-1, 1])
                else:
                    y += random.choice([-1, 1])
            else:
                if random.random() < 0.5:
                    x += random.choice([-1, 1])
                else:
                    y += random.choice([-1, 1])

            if x < 1 or x >= gw - 1 or y < 1 or y >= gh - 1:
                x = random.randint(0, gw - 1)
                y = random.randint(0, gh - 1)

        if i % 40 == 0:
            render_base(screen)
            screen.blit(layer, (0, 0))
            pygame.display.flip()
            clock.tick(60)

    render_base(screen)
    screen.blit(layer, (0, 0))
    pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Crystal Growth Variants")
    clock = pygame.time.Clock()

    render_base(screen)
    pygame.display.flip()

    draw_stamped_prisms(screen, clock)
    save_frame(screen, "stamped")
    time.sleep(0.4)

    draw_growing_rods(screen, clock)
    save_frame(screen, "rods")
    time.sleep(0.4)

    draw_rect_dla(screen, clock)
    save_frame(screen, "dla")

    # Keep the window open briefly after finishing
    end_time = time.time() + 1.5
    while time.time() < end_time:
        handle_events()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
