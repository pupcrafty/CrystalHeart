class_name FluidParticle

@export var pos: Vector2
@export var vel: Vector2
@export var parent_emmiter_index: int

var deceleraton:float = 0.1
var age: float = 0.0
var size: float = 10.0
var lifetime: float = 20.0


var attract_repel_force = 100


func step(delta: float) -> void:
	pos += vel * delta
	age += delta
	vel-= vel*(deceleraton)*delta


func is_dead() -> bool:
	return age >= lifetime

func interact(particle: FluidParticle, delta: float)->void:
	var direction: Vector2 = particle.pos-pos
	
	var dist2 = direction.length_squared()
	
	if dist2<0.00001 or dist2>size**2:
		return
	
	var intensity: float = ((size/2)-sqrt(dist2))/(size/2)
	attract_repulse(particle, intensity, direction, delta)
	

func attract_repulse(particle:FluidParticle, intensity:float, direction: Vector2, delta:float)-> void:
	vel-= attract_repel_force*intensity*delta*direction.normalized()
	particle.vel+= attract_repel_force*intensity*delta*direction.normalized()
	
func combine_velocities(particle:FluidParticle, intensity:float)->void:
	vel+=10*particle.vel*(1-intensity)
	particle.vel+=10*vel*(1-intensity)
