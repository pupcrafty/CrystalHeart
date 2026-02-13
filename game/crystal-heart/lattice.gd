extends Node2D
class_name Lattice

var slots_available_per_particle: Array[int] = [2,3,4,5,6]
@export var slots: int 
@export var slot_spacing: float = 20.0
@export var capture_radius: float = 14.0
@export var max_conversions_per_frame: int = 4
@export var slot_draw_radius: float = 3.0
@export var slot_dir_draw_length: float = 12.0
@export var slot_color: Color = Color(0.2, 0.9, 1.0, 1.0)
@export var slot_dir_color: Color = Color(1.0, 0.7, 0.2, 1.0)
@export var particle_draw_radius: float = 5.0
@export var particle_color: Color = Color(0.25, 0.45, 1.0, 1.0)
@export var particle_min_distance_factor: float = 0.8

var boundary_points: PackedVector2Array = PackedVector2Array()
var frontier_slots: Array[LatticeSlot] = []
var placed_particles: Array[LatticeParticle] = []
var is_crystallizing: bool = false

@onready var layer_control: CrystalLayerControl = $".."

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	pass # Replace with function body.


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	if not is_crystallizing:
		return
	var changed: bool = convert_nearby_fluid_particles()
	if changed:
		queue_redraw()


func _draw() -> void:
	for slot: LatticeSlot in frontier_slots:
		draw_circle(slot.pos, slot_draw_radius, slot_color)
		var dir_end: Vector2 = slot.pos + slot.dir * slot_dir_draw_length
		draw_line(slot.pos, dir_end, slot_dir_color, 1.5)

	for particle: LatticeParticle in placed_particles:
		if particle.draw_this:
			draw_circle(particle.pos, particle_draw_radius, particle_color)

func begin_crystalization(corners: PackedVector2Array)->void:
	boundary_points = corners.duplicate()
	frontier_slots.clear()
	placed_particles.clear()
	is_crystallizing = true

	slots = int(slots_available_per_particle.pick_random())
	print("Slots chosen: ", slots)
	var perimeter: float = calculate_perimeter(boundary_points)
	print("Perimeter =", perimeter)
	print("Target slot spacing =", slot_spacing)
	generate_even_frontier_slot_positions()
	print("Frontier slots generated =", frontier_slots.size())
	queue_redraw()


func calculate_perimeter(corners: PackedVector2Array) -> float:
	if corners.size() < 2:
		return 0.0

	var total_perimeter: float = 0.0
	for i in range(0, corners.size()):
		var next_index: int = (i + 1) % corners.size()
		total_perimeter += corners[i].distance_to(corners[next_index])
	return total_perimeter


func generate_even_frontier_slot_positions() -> void:
	frontier_slots.clear()

	if boundary_points.size() < 2:
		return

	var perimeter: float = calculate_perimeter(boundary_points)
	if perimeter <= 0.0:
		return

	var polygon_center: Vector2 = get_polygon_center(boundary_points)
	var slot_count: int = max(1, int(floor(perimeter / slot_spacing)))
	var actual_spacing: float = perimeter / float(slot_count)

	for k in range(0, slot_count):
		var arc_distance: float = float(k) * actual_spacing
		var sample: LatticePerimeterSample = sample_perimeter_at_distance(boundary_points, arc_distance)
		var outward_dir: Vector2 = compute_outward_normal(sample.pos, sample.tangent, polygon_center)
		frontier_slots.append(LatticeSlot.new(sample.pos, outward_dir, false))


func convert_nearby_fluid_particles() -> bool:
	var emitter_array: EmitterArray = layer_control.emitter_array
	if emitter_array == null:
		return false
	if emitter_array.particles.is_empty():
		return false

	var consumed_particle_indices: Array[int] = []
	var conversions: int = 0
	var changed: bool = false

	for slot: LatticeSlot in frontier_slots:
		if conversions >= max_conversions_per_frame:
			break
		if slot.filled:
			continue

		var candidate_pos: Vector2 = slot.pos + slot.dir * slot_spacing
		var fluid_index: int = find_nearby_fluid_particle_index(
			emitter_array.particles,
			candidate_pos,
			capture_radius,
			consumed_particle_indices
		)
		if fluid_index == -1:
			continue

		var placed_particle: LatticeParticle = LatticeParticle.new()
		placed_particle.pos = candidate_pos
		placed_particle.is_frontier = true
		placed_particles.append(placed_particle)

		slot.filled = true
		consumed_particle_indices.append(fluid_index)
		conversions += 1
		changed = true

		generate_frontier_slots_from_particle(placed_particle, slot.dir)

	if consumed_particle_indices.is_empty():
		return changed

	consumed_particle_indices.sort()
	consumed_particle_indices.reverse()
	for particle_index: int in consumed_particle_indices:
		emitter_array.particles.remove_at(particle_index)

	return true


func find_nearby_fluid_particle_index(
	particles: Array[FluidParticle],
	target_pos: Vector2,
	max_radius: float,
	ignore_indices: Array[int]
) -> int:
	var max_radius_squared: float = max_radius * max_radius
	var best_index: int = -1
	var best_distance_squared: float = INF

	for index in range(0, particles.size()):
		if ignore_indices.has(index):
			continue
		var particle: FluidParticle = particles[index]
		var dist2: float = particle.pos.distance_squared_to(target_pos)
		if dist2 > max_radius_squared:
			continue
		if dist2 < best_distance_squared:
			best_distance_squared = dist2
			best_index = index

	return best_index


func generate_frontier_slots_from_particle(particle: LatticeParticle, incoming_dir: Vector2) -> void:
	var effective_slots: int = max(3, slots)
	var angle_step: float = TAU / float(effective_slots)
	var base_angle: float = incoming_dir.angle()
	var back_dir: Vector2 = -incoming_dir.normalized()
	particle.open_slots.clear()

	for slot_index in range(0, effective_slots):
		var dir: Vector2 = Vector2.RIGHT.rotated(base_angle + float(slot_index) * angle_step).normalized()
		if dir.dot(back_dir) > 0.95:
			continue
		var new_slot: LatticeSlot = add_frontier_slot_if_valid(particle.pos, dir)
		if new_slot != null:
			particle.open_slots.append(new_slot)


func add_frontier_slot_if_valid(origin_pos: Vector2, dir: Vector2) -> LatticeSlot:
	var min_distance: float = slot_spacing * particle_min_distance_factor
	var candidate_pos: Vector2 = origin_pos + dir * slot_spacing
	if not can_place_particle_at(candidate_pos, min_distance):
		return null
	if has_open_slot_for_target(candidate_pos, min_distance):
		return null

	var new_slot: LatticeSlot = LatticeSlot.new(origin_pos, dir, false)
	frontier_slots.append(new_slot)
	return new_slot


func has_open_slot_for_target(target_pos: Vector2, min_distance: float) -> bool:
	var min_distance_squared: float = min_distance * min_distance
	for slot: LatticeSlot in frontier_slots:
		if slot.filled:
			continue
		var slot_target: Vector2 = slot.pos + slot.dir * slot_spacing
		if slot_target.distance_squared_to(target_pos) < min_distance_squared:
			return true
	return false


func can_place_particle_at(candidate_pos: Vector2, min_distance: float) -> bool:
	var min_distance_squared: float = min_distance * min_distance
	for particle: LatticeParticle in placed_particles:
		if particle.pos.distance_squared_to(candidate_pos) < min_distance_squared:
			return false
	return true


func point_on_perimeter_at_distance(corners: PackedVector2Array, distance_along: float) -> Vector2:
	return sample_perimeter_at_distance(corners, distance_along).pos


func sample_perimeter_at_distance(corners: PackedVector2Array, distance_along: float) -> LatticePerimeterSample:
	var perimeter: float = calculate_perimeter(corners)
	if perimeter <= 0.0:
		return LatticePerimeterSample.new(Vector2.ZERO, Vector2.RIGHT)

	var target: float = fposmod(distance_along, perimeter)
	var traversed: float = 0.0

	for i in range(0, corners.size()):
		var a: Vector2 = corners[i]
		var b: Vector2 = corners[(i + 1) % corners.size()]
		var edge_vector: Vector2 = b - a
		var edge_length: float = edge_vector.length()
		if edge_length <= 0.0:
			continue

		if traversed + edge_length >= target:
			var local: float = target - traversed
			var t: float = local / edge_length
			var sample_pos: Vector2 = a.lerp(b, t)
			var tangent: Vector2 = edge_vector / edge_length
			return LatticePerimeterSample.new(sample_pos, tangent)

		traversed += edge_length

	var fallback_tangent: Vector2 = (corners[1] - corners[0]).normalized()
	if fallback_tangent == Vector2.ZERO:
		fallback_tangent = Vector2.RIGHT
	return LatticePerimeterSample.new(corners[0], fallback_tangent)


func get_polygon_center(corners: PackedVector2Array) -> Vector2:
	if corners.size() == 0:
		return Vector2.ZERO

	var center: Vector2 = Vector2.ZERO
	for corner in corners:
		center += corner
	return center / float(corners.size())


func compute_outward_normal(sample_pos: Vector2, tangent: Vector2, polygon_center: Vector2) -> Vector2:
	var tangent_dir: Vector2 = tangent.normalized()
	if tangent_dir == Vector2.ZERO:
		return Vector2.RIGHT

	var normal_a: Vector2 = Vector2(-tangent_dir.y, tangent_dir.x)
	var normal_b: Vector2 = Vector2(tangent_dir.y, -tangent_dir.x)
	var from_center: Vector2 = sample_pos - polygon_center

	if from_center.dot(normal_a) >= from_center.dot(normal_b):
		return normal_a
	return normal_b
