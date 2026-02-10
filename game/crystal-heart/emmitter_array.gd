extends Node2D
class_name EmmitterArray
# Holds particles
var particles :Array[FluidParticle] = []

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	pass # Replace with function body.


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	var clean_up_list: Array[int]= []
	for index in range(0,particles.size()):
		var particle : FluidParticle = particles.get(index)
		if particle.is_dead():
			clean_up_list.append(index)
		else:
			particle.step(delta)
	clean_up_list.sort()
	clean_up_list.reverse()
	for index in clean_up_list:
		particles.remove_at(index)		
	# Ensure draw updates every frame as particles move.
	queue_redraw()

func _draw():
	for particle in particles:
		draw_circle(particle.pos, particle.size, Color(0.3, 0.3, 1, 1))

func add_particle(particle: FluidParticle)->void:
	particles.append(particle)
