# PythonTest3

Layered crystal renderer for Godot `shapes.json` runs.

## What it does

- Loads shape history from a Godot run JSON.
- Uses each shape's `color` field (`r,g,b,a`) when present.
- Facets the internal area of each shape with deterministic crystal shards.
- Layers shapes so **smallest + oldest end up on top**.
- Keeps original shape boundaries (no boundary faceting).

## plausable_1 (new default)

`--style plausable_1` builds thick growth bands between consecutive saved shapes.
It now also varies angular sections so different parts read as different crystal types, with deterministic intercolor breakup.

```bash
cd /Users/craftyfillmore/Desktop/Workspace/CrystalHeart/PythonTest3
python3 facet_polygon_demo.py --style plausable_1 --out output/latest_accretion_style.svg
```

## Other options

- `--style accretion` is kept as an alias for `plausable_1`.
- `--style plausable_2` uses non-radial difference triangles with pseudo lighting from the original shape.
- `--style geode` for shell/core internal faceting.
- `--style classic` for the earlier single-band facet style.
- `--min-facet-lightness 0.40` to drop darkest triangles.
- `--prev-boundary-strength 0.70` to pull each layer toward the previous boundary.
- `--prev-boundary-max-growth 1.28` to cap how much farther out each layer can grow.
- `--hue` / `--sat` are fallback colors when JSON has no `color`.
- `--seed` controls deterministic variation.

## Run a specific run folder

```bash
python3 facet_polygon_demo.py \
  --input "/Users/craftyfillmore/Library/Application Support/Godot/app_userdata/CrystalHeart/crystal_shapes/run_1771166042_288" \
  --style geode \
  --out output/run_1771166042_288_geode.svg
```

## Progressive plausable_2 build outputs

```bash
python3 facet_polygon_demo.py \
  --style plausable_2 \
  --input "/Users/craftyfillmore/Library/Application Support/Godot/app_userdata/CrystalHeart/crystal_shapes/run_1771174001_346" \
  --progressive-output-dir output/run_1771174001_346_plausable_2_steps \
  --out output/run_1771174001_346_plausable_2_final.svg
```
