class_name FluidParticle

@export var pos: Vector2 = Vector2.ZERO
@export var vel: Vector2 = Vector2.ZERO
@export var parent_emmiter_index: int = -1

var deceleraton: float = 0.1
var age: float = 0.0
var size: float = 10.0
var lifetime: float = 120.0
var shape_attract_acceleration: float = 1.0

var attract_repel_force: float = 40.0


func step(delta: float) -> void:
	pos += vel * delta
	age += delta
	vel -= vel * deceleraton * delta


func is_dead() -> bool:
	return age >= lifetime or pos.x < 0

func interact(particle: FluidParticle, delta: float) -> void:
	var direction: Vector2 = particle.pos - pos

	var dist2: float = direction.length_squared()

	if dist2 < 0.00001 or dist2 > size ** 2:
		return

	var intensity: float = ((size / 2.0) - sqrt(dist2)) / (size / 2.0)
	attract_repulse(particle, intensity, direction, delta)

func attract_repulse(particle: FluidParticle, intensity: float, direction: Vector2, delta: float) -> void:
	vel -= attract_repel_force * intensity * delta * direction.normalized()
	particle.vel += attract_repel_force * intensity * delta * direction.normalized()

func combine_velocities(particle: FluidParticle, intensity: float) -> void:
	vel += 10.0 * particle.vel * (1.0 - intensity)
	particle.vel += 10.0 * vel * (1.0 - intensity)

func attract_to_shape_point(target_point: Vector2, delta: float) -> void:
	if target_point == pos:
		return
	var direction: Vector2 = target_point - pos
	direction = direction.normalized()
	vel += delta * direction * shape_attract_acceleration
