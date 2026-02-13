extends Node2D
class_name Lattice

var slots_available_per_particle: Array[int] = [2,3,4,5,6]
@export var slots: int 
@export var slot_spacing: float = 20.0
@export var capture_radius: float = 14.0
@export var max_conversions_per_frame: int = 4
@export var completion_timeout_seconds: float = 0.5
@export var slot_draw_radius: float = 3.0
@export var slot_dir_draw_length: float = 12.0
@export var slot_color: Color = Color(0.2, 0.9, 1.0, 1.0)
@export var slot_dir_color: Color = Color(1.0, 0.7, 0.2, 1.0)
@export var particle_draw_radius: float = 5.0
@export var particle_color: Color = Color(0.25, 0.45, 1.0, 1.0)
@export var particle_min_distance_factor: float = 0.8
@export var perimeter_max_vertices: int = 16
@export var perimeter_min_vertex_spacing_factor: float = 0.9

var boundary_points: PackedVector2Array = PackedVector2Array()
var frontier_slots: Array[LatticeSlot] = []
var placed_particles: Array[LatticeParticle] = []
var is_crystallizing: bool = false
var time_without_conversion: float = 0.0

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
		time_without_conversion = 0.0
		queue_redraw()
	else:
		time_without_conversion += delta
		if time_without_conversion >= completion_timeout_seconds:
			complete_crystalization()


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
	time_without_conversion = 0.0

	slots = int(slots_available_per_particle.pick_random())
	print("Slots chosen: ", slots)
	var perimeter: float = calculate_perimeter(boundary_points)
	print("Perimeter =", perimeter)
	print("Target slot spacing =", slot_spacing)
	generate_even_frontier_slot_positions()
	print("Frontier slots generated =", frontier_slots.size())
	queue_redraw()


func complete_crystalization() -> void:
	is_crystallizing = false
	layer_control.handle_crystalization_complete(build_vertex_points_from_particles())
	print("Crystalization complete. Placed particles =", placed_particles.size())


func build_vertex_points_from_particles() -> PackedVector2Array:
	if placed_particles.size() < 3:
		return boundary_points.duplicate()

	var perimeter_points: Array[Vector2] = collect_perimeter_points_from_frontier()
	if perimeter_points.size() >= 3:
		var ordered_points: PackedVector2Array = sort_points_around_center(perimeter_points)
		var simplified_points: PackedVector2Array = simplify_straight_runs(ordered_points)
		simplified_points = simplify_by_spacing(simplified_points, slot_spacing * perimeter_min_vertex_spacing_factor)
		simplified_points = reduce_to_max_vertices(simplified_points, perimeter_max_vertices)
		if simplified_points.size() >= 3:
			return enforce_points_outside_polygon(simplified_points, boundary_points)

	var points: Array[Vector2] = []
	for particle: LatticeParticle in placed_particles:
		append_unique_point(points, particle.pos, slot_spacing * 0.2)

	return enforce_points_outside_polygon(convex_hull(points), boundary_points)


func collect_perimeter_points_from_frontier() -> Array[Vector2]:
	var perimeter_points: Array[Vector2] = []
	var offset: float = slot_spacing * 0.5
	var merge_distance: float = slot_spacing * 0.35

	for slot: LatticeSlot in frontier_slots:
		if slot.filled:
			continue
		var dir: Vector2 = slot.dir.normalized()
		if dir == Vector2.ZERO:
			continue
		# Use a half-step along open frontier directions to sample the current crystal perimeter.
		var perimeter_point: Vector2 = slot.pos + dir * offset
		append_unique_point(perimeter_points, perimeter_point, merge_distance)

	return perimeter_points


func append_unique_point(points: Array[Vector2], candidate: Vector2, min_distance: float) -> void:
	var min_distance_squared: float = min_distance * min_distance
	for point: Vector2 in points:
		if point.distance_squared_to(candidate) < min_distance_squared:
			return
	points.append(candidate)


func sort_points_around_center(points: Array[Vector2]) -> PackedVector2Array:
	var center: Vector2 = Vector2.ZERO
	for point: Vector2 in points:
		center += point
	center /= float(points.size())

	var sorted_points: Array[Vector2] = points.duplicate()
	sorted_points.sort_custom(func(a: Vector2, b: Vector2) -> bool:
		var angle_a: float = atan2(a.y - center.y, a.x - center.x)
		var angle_b: float = atan2(b.y - center.y, b.x - center.x)
		return angle_a < angle_b
	)

	var result: PackedVector2Array = PackedVector2Array()
	for point: Vector2 in sorted_points:
		result.append(point)
	return result


func simplify_straight_runs(points: PackedVector2Array) -> PackedVector2Array:
	if points.size() <= 3:
		return points.duplicate()

	var reduced: Array[Vector2] = []
	for point: Vector2 in points:
		reduced.append(point)

	var max_distance_from_line: float = slot_spacing * 0.08
	var min_direction_dot: float = 0.98
	var changed: bool = true

	while changed and reduced.size() > 3:
		changed = false
		var count: int = reduced.size()
		for i in range(0, count):
			var prev_index: int = (i - 1 + count) % count
			var next_index: int = (i + 1) % count
			var prev: Vector2 = reduced[prev_index]
			var curr: Vector2 = reduced[i]
			var next: Vector2 = reduced[next_index]

			if is_straight_run_point(prev, curr, next, max_distance_from_line, min_direction_dot):
				reduced.remove_at(i)
				changed = true
				break

	var result: PackedVector2Array = PackedVector2Array()
	for point: Vector2 in reduced:
		result.append(point)
	return result


func is_straight_run_point(
	prev: Vector2,
	curr: Vector2,
	next: Vector2,
	max_distance_from_line: float,
	min_direction_dot: float
) -> bool:
	var seg_a: Vector2 = curr - prev
	var seg_b: Vector2 = next - curr
	if seg_a == Vector2.ZERO or seg_b == Vector2.ZERO:
		return true

	var dir_a: Vector2 = seg_a.normalized()
	var dir_b: Vector2 = seg_b.normalized()
	if dir_a.dot(dir_b) < min_direction_dot:
		return false

	var line: Vector2 = next - prev
	var line_length: float = line.length()
	if line_length <= 0.0:
		return true

	var distance: float = abs(cross(prev, next, curr)) / line_length
	return distance <= max_distance_from_line


func simplify_by_spacing(points: PackedVector2Array, min_spacing: float) -> PackedVector2Array:
	if points.size() <= 3:
		return points.duplicate()

	var spacing: float = max(0.001, min_spacing)
	var spacing_squared: float = spacing * spacing
	var kept: Array[Vector2] = []

	for i in range(0, points.size()):
		var point: Vector2 = points[i]
		if kept.is_empty():
			kept.append(point)
			continue
		var last_kept: Vector2 = kept[kept.size() - 1]
		if last_kept.distance_squared_to(point) >= spacing_squared:
			kept.append(point)

	if kept.size() >= 2:
		var first_point: Vector2 = kept[0]
		var last_point: Vector2 = kept[kept.size() - 1]
		if first_point.distance_squared_to(last_point) < spacing_squared:
			kept.remove_at(kept.size() - 1)

	if kept.size() < 3:
		return points.duplicate()

	var result: PackedVector2Array = PackedVector2Array()
	for point: Vector2 in kept:
		result.append(point)
	return result


func reduce_to_max_vertices(points: PackedVector2Array, max_vertices: int) -> PackedVector2Array:
	if points.size() <= 3:
		return points.duplicate()
	if max_vertices < 3 or points.size() <= max_vertices:
		return points.duplicate()

	var working: Array[Vector2] = []
	for point: Vector2 in points:
		working.append(point)

	while working.size() > max_vertices and working.size() > 3:
		var best_index: int = -1
		var smallest_area: float = INF
		var count: int = working.size()

		for i in range(0, count):
			var prev: Vector2 = working[(i - 1 + count) % count]
			var curr: Vector2 = working[i]
			var next: Vector2 = working[(i + 1) % count]
			var tri_area: float = abs(cross(prev, curr, next))
			if tri_area < smallest_area:
				smallest_area = tri_area
				best_index = i

		if best_index == -1:
			break
		working.remove_at(best_index)

	var result: PackedVector2Array = PackedVector2Array()
	for point: Vector2 in working:
		result.append(point)
	return result


func enforce_points_outside_polygon(points: PackedVector2Array, polygon: PackedVector2Array) -> PackedVector2Array:
	if points.size() == 0 or polygon.size() < 3:
		return points.duplicate()

	var center: Vector2 = get_polygon_center(polygon)
	var min_clearance: float = slot_spacing * 0.12
	var step_distance: float = slot_spacing * 0.25
	var max_steps: int = 12
	var result: PackedVector2Array = PackedVector2Array()

	for point: Vector2 in points:
		var adjusted: Vector2 = point
		var step_index: int = 0
		while step_index < max_steps and is_inside_or_too_close_to_polygon(adjusted, polygon, min_clearance):
			var outward_dir: Vector2 = (adjusted - center).normalized()
			if outward_dir == Vector2.ZERO:
				outward_dir = Vector2.RIGHT
			adjusted += outward_dir * step_distance
			step_index += 1
		result.append(adjusted)

	return result


func is_inside_or_too_close_to_polygon(point: Vector2, polygon: PackedVector2Array, min_clearance: float) -> bool:
	if Geometry2D.is_point_in_polygon(point, polygon):
		return true

	var min_distance_squared: float = min_distance_squared_to_polygon_edges(point, polygon)
	return min_distance_squared <= min_clearance * min_clearance


func min_distance_squared_to_polygon_edges(point: Vector2, polygon: PackedVector2Array) -> float:
	if polygon.size() < 2:
		return INF

	var min_distance_squared: float = INF
	for i in range(0, polygon.size()):
		var a: Vector2 = polygon[i]
		var b: Vector2 = polygon[(i + 1) % polygon.size()]
		var closest: Vector2 = Geometry2D.get_closest_point_to_segment(point, a, b)
		var dist_squared: float = point.distance_squared_to(closest)
		if dist_squared < min_distance_squared:
			min_distance_squared = dist_squared

	return min_distance_squared


func convex_hull(points: Array[Vector2]) -> PackedVector2Array:
	if points.size() < 3:
		var fallback: PackedVector2Array = PackedVector2Array()
		for point: Vector2 in points:
			fallback.append(point)
		return fallback

	points.sort_custom(func(a: Vector2, b: Vector2) -> bool:
		if is_equal_approx(a.x, b.x):
			return a.y < b.y
		return a.x < b.x
	)

	var lower: Array[Vector2] = []
	for point: Vector2 in points:
		while lower.size() >= 2 and cross(lower[lower.size() - 2], lower[lower.size() - 1], point) <= 0.0:
			lower.pop_back()
		lower.append(point)

	var upper: Array[Vector2] = []
	for i in range(points.size() - 1, -1, -1):
		var point: Vector2 = points[i]
		while upper.size() >= 2 and cross(upper[upper.size() - 2], upper[upper.size() - 1], point) <= 0.0:
			upper.pop_back()
		upper.append(point)

	if not lower.is_empty():
		lower.pop_back()
	if not upper.is_empty():
		upper.pop_back()

	var hull_points: PackedVector2Array = PackedVector2Array()
	for point: Vector2 in lower:
		hull_points.append(point)
	for point: Vector2 in upper:
		hull_points.append(point)

	return hull_points


func cross(origin: Vector2, a: Vector2, b: Vector2) -> float:
	var oa: Vector2 = a - origin
	var ob: Vector2 = b - origin
	return oa.x * ob.y - oa.y * ob.x


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
