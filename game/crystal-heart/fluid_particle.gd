class_name FluidParticle

var pos: Vector2
var vel: Vector2
var deceleraton: Vector2 = Vector2(100, 100)
var age: float = 0.0
var size: float = 10.0
var lifetime: float = 3.0

func step(delta: float) -> void:
	pos += vel * delta
	age += delta
	vel -= delta*deceleraton
	print("Particle Location: x=",pos.x, ", y= ", pos.y)
	print("Particle Velocity: x=",vel.x, ", y= ", vel.y)

func is_dead() -> bool:
	return age >= lifetime
