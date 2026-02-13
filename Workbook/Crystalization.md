Perfect. Let’s reduce this to **clean, lattice-driving primitives** that match your crystallization model and plug directly into your Godot crystal growth system.

You already defined the core process:

1. Evenly spaced attachment points (slots)
2. Attach nearby sprites to slots
3. Use their empty slots
4. Repeat outward
5. Clear floaters

Now we formalize the **lattice logic** underneath it.

---

# 🧊 Core Crystal Latticing Concepts

## 1️⃣ Regular Angular Connections (The Slot Rule)

Each sprite has **N evenly spaced attachment slots** around its center.

### Concept:

If a sprite has `N` slots:

```
angle_step = TAU / N
slot_angle_i = base_rotation + i * angle_step
```

So for:

* Hex lattice → N = 6 (60° spacing)
* Square lattice → N = 4 (90° spacing)
* Triangular → N = 3 (120° spacing)

This gives you **angular quantization**.

No arbitrary angles.
Everything snaps to the nearest valid slot direction.

This prevents organic blobbing and forces crystalline order.

---

## 2️⃣ Edge-Driven Growth (Start at Shape Boundary)

You don’t grow from random free particles.

You:

### Step A:

Generate slots evenly spaced around the **initial shape edge**.

That shape could be:

* Circle
* Polygon
* Convex hull
* Arbitrary collision polygon

For each edge point:

```
slot.position = edge_point
slot.normal = outward_normal
```

These normals determine the initial outward growth directions.

This creates your **seed frontier**.

---

## 3️⃣ Connection Rule (Distance + Angle Agreement)

A particle can attach if:

1. It is within range of a slot.
2. Its center aligns to the slot direction.
3. It does not overlap existing placed sprites.

Mathematically:

```
candidate_position = slot.position + slot.direction * radius * 2
```

You don’t search free space.

You compute the **exact expected position** from the slot.

This is the key difference from fluid simulation.

Crystal growth is:

> Deterministic slot filling
> Not force-based convergence.

---

## 4️⃣ Frontier Expansion (The Recursive Step)

When a sprite attaches:

* Mark used slot as filled
* Generate its own N slots
* Add those empty slots to the frontier list

Frontier = all unfilled slots exposed to space.

Repeat:

```
while frontier not empty:
    try fill slots
```

This matches your earlier crystallization step definition exactly.

---

## 5️⃣ Preventing Disorder

To keep it crystalline:

### A) No free-angle rotation

Each sprite’s rotation must match the slot orientation.

### B) Snap rotation to lattice

```
sprite.rotation = slot.angle
```

### C) No sliding

Position is computed from slot geometry only.

---

# 🧩 How This Connects to Your Circle Packing Work

Your earlier circle packing system:

* Used tangent intersections
* Solved for valid contact points
* Used distance from center to affect size

This lattice system is the discrete version.

Packing = continuous geometry
Lattice = discrete angular geometry

You can combine them:

* Radius scales with distance from center
* But connection directions remain quantized

That gives you **growing faceted crystals instead of blobs**.

---

# 🧠 Minimal Conceptual Algorithm

High-level only:

```
Initialize seed shape
Generate edge slots
Add to frontier

Loop:
    For each slot in frontier:
        Compute exact attachment position
        If no overlap:
            Place sprite
            Generate its slots
            Add new slots to frontier
        Mark slot as processed

Clear floating particles
```

---

# 🔷 Key Mental Model

Fluid system:

> Particles move until they find energy minimum.

Crystal system:

> Geometry decides the only allowed placements.

You are not simulating physics.
You are enforcing geometry.


