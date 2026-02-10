extends Node2D

@onready var parent_array :EmmitterArray = $".."

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	emit_one()
	pass # Replace with function body.


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	draw_circle(global_position, 6.0, Color(255, 0, 0, 0.5))
	pass

func _draw():
	draw_circle(global_position, 6.0, Color(255, 0, 0, 0.5))
	
func emit_one():
	var p :FluidParticle = FluidParticle.new()
	p.pos = position
	p.vel = Vector2.RIGHT * 200
	parent_array.add_particle(p)
	
