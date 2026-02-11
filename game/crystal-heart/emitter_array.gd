extends Node2D
class_name EmitterArray
# Holds particles
var particles :Array[FluidParticle] = []
var emitters: Array[LiquidEmitter] = []

@onready var layer_control: CrystalLayerControl = $".."

var count_down = 0.1
var emit_base_speed = 10

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
	count_down = clampf(count_down-delta, 0, 1)
	if count_down ==0:
		count_down = 1
		emit_particles()
	
	queue_redraw()

func _draw():
	for particle in particles:
		draw_circle(particle.pos, particle.size, Color(0.3, 0.3, 1, 1))
		
	for emitter in emitters:
		draw_circle(emitter.pos, 10, Color(1, 0.5, 0, 1))

func add_particle(particle: FluidParticle)->void:
	particles.append(particle)

func emit_particles()->void:
	for emitter in emitters:
		particles.append(emitter.emit_one(100))
		
func apply_particle_interactions(delta: float)->void:
	var particle_num : int = particles.size()
	for i in range(0, particle_num):
		for j in range(i+1, particle_num):
			var particle_i :FluidParticle = particles.get(i)
			var particle_j :FluidParticle = particles.get(j)
			particle_i.ineract(particle_j,delta)
