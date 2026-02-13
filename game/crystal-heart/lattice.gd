extends Node2D
class_name Lattice

var slots_available_per_particle: Array[int] = [2,3,4,5,6]
@export var slots: int 
@export var slot_spacing: float = 20.0

var boundary_points: PackedVector2Array = PackedVector2Array()
var frontier_slots: Array[LatticeSlot] = []

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	pass # Replace with function body.


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	pass

func begin_crystalization(corners: PackedVector2Array)->void:
	boundary_points = corners.duplicate()
	frontier_slots.clear()

	slots = int(slots_available_per_particle.pick_random())
	print("Slots chosen: ", slots)
	var perimeter: float = calculate_perimeter(boundary_points)
	print("Perimeter =", perimeter)
	print("Target slot spacing =", slot_spacing)
	generate_even_frontier_slot_positions()
	print("Frontier slots generated =", frontier_slots.size())


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
