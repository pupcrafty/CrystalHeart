extends Node2D
class_name EmitterArray
# Holds particles
var particles: Array[FluidParticle] = []
var emitters: Array[LiquidEmitter] = []

@onready var layer_control: CrystalLayerControl = $".."

var count_down: float = 0.1
var emit_base_speed: float = 10.0
var emit_crowd_multiplier: float = 5.0
var crystalize_outward_acceleration: float = 200.0

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	pass # Replace with function body.


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	var clean_up_list: Array[int] = []
	for index in range(0, particles.size()):
		var particle: FluidParticle = particles.get(index)
		if particle.is_dead():
			clean_up_list.append(index)
		else:
			particle.step(delta)
			if layer_control.crystalizing:
				apply_crystalize_repel(particle, delta)
			else:
				apply_shape_attract(particle, delta)
	apply_particle_interactions(delta)
	clean_up_list.sort()
	clean_up_list.reverse()
	for index in clean_up_list:
		particles.remove_at(index)
	# Ensure draw updates every frame as particles move.
	count_down = clampf(count_down - delta, 0.0, 1.0)
	if count_down == 0.0:
		count_down = 1.0
		if not layer_control.crystalizing:
			emit_particles()

	queue_redraw()

func _draw() -> void:
	for particle in particles:
		draw_circle(particle.pos, particle.size, Color(0.3, 0.3, 1, 1))

	for emitter in emitters:
		draw_circle(emitter.pos, 10, Color(1, 0.5, 0, 1))

func add_particle(particle: FluidParticle) -> void:
	particles.append(particle)

func emit_particles() -> void:
	var y_velocity_offset: float = randf() / 2.0 - 0.25
	for emitter in emitters:
		var crowd: int = get_emmiter_crowd(emitter)
		var speed: float = emit_base_speed + float(crowd) * emit_crowd_multiplier
		var particle: FluidParticle = emitter.emit_one(speed, y_velocity_offset)
		particle.parent_emmiter_index = emitters.find(emitter)
		particles.append(particle)

func apply_particle_interactions(delta: float) -> void:
	var particle_num: int = particles.size()
	for i in range(0, particle_num):
		for j in range(i + 1, particle_num):
			var particle_i: FluidParticle = particles.get(i)
			var particle_j: FluidParticle = particles.get(j)
			particle_i.interact(particle_j, delta)

func apply_shape_attract(particle: FluidParticle, delta: float) -> void:
	var parent_index: int = particle.parent_emmiter_index
	var back_one_index: int = parent_index - 1
	var forward_one_index: int = parent_index + 1
	if back_one_index == -1:
		back_one_index = emitters.size() - 1
	if forward_one_index == emitters.size():
		forward_one_index = 0

	var emitter_positions: Array[Vector2] = []
	emitter_positions.append(emitters[parent_index].pos)
	emitter_positions.append(emitters[back_one_index].pos)
	emitter_positions.append(emitters[forward_one_index].pos)

	var closest_two_emitter_locations: Array[Vector2] = closest_two(particle.pos, emitter_positions)
	var target_point: Vector2 = closest_point_on_emmiter_segment(particle.pos, closest_two_emitter_locations[0], closest_two_emitter_locations[1])
	particle.attract_to_shape_point(target_point, delta)

func apply_crystalize_repel(particle: FluidParticle, delta: float) -> void:
	var crystal_center: Vector2 = get_crystal_center()
	var direction: Vector2 = particle.pos - crystal_center
	if direction == Vector2.ZERO:
		direction = Vector2.RIGHT
	else:
		direction = direction.normalized()
	particle.vel += direction * crystalize_outward_acceleration * delta

func closest_two(reference: Vector2, points: Array[Vector2]) -> Array[Vector2]:
	var sorted_points: Array[Vector2] = points.duplicate()

	sorted_points.sort_custom(func(a: Vector2, b: Vector2) -> bool:
		return reference.distance_squared_to(a) < reference.distance_squared_to(b)
	)

	var result: Array[Vector2] = []
	result.append(sorted_points[0])
	result.append(sorted_points[1])
	return result

func closest_point_on_emmiter_segment(refrence_point: Vector2, emitter_a: Vector2, emitter_b: Vector2) -> Vector2:
	var ab: Vector2 = emitter_b - emitter_a
	var ap: Vector2 = refrence_point - emitter_a

	var ab_len_squared: float = ab.length_squared()

	# Handle degenerate case (A == B)
	if ab_len_squared == 0.0:
		return emitter_a

	var t: float = ap.dot(ab) / ab_len_squared
	t = clampf(t, 0.0, 1.0)

	return emitter_a + ab * t

func get_emmiter_crowd(emitter: LiquidEmitter) -> int:
	var count: int = 0
	for particle in particles:
		var dist: float = (particle.pos - emitter.pos).length_squared()
		var sizes_squared: float = (particle.size + emitter.size) ** 2
		if dist < sizes_squared:
			count += 1
	return count

func get_crystal_center() -> Vector2:
	var points: PackedVector2Array = layer_control.crystal_points.vertex_points
	if points.size() == 0:
		return Vector2.ZERO
	var center: Vector2 = Vector2.ZERO
	for point in points:
		center += point
	return center / float(points.size())
