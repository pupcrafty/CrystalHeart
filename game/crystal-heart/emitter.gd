class_name LiquidEmitter

var pos: Vector2
var emit_angle: float
var emit_angular_varience: float = PI/5
# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	pass # Replace with function body.

func emit_one(speed: float) -> FluidParticle:
	var p :FluidParticle = FluidParticle.new()
	p.pos = pos
	var angle_varience: float = (0.5 - randf())*emit_angular_varience
	p.vel = Vector2.from_angle(emit_angle+angle_varience) * speed
	return p

func set_position(in_pos:Vector2)->void:
	pos = in_pos
	
func set_emit_angle(angle:float)->void:
	emit_angle = angle

func emit_many(count: int, speed:float)-> Array[FluidParticle]:
	var particles : Array[FluidParticle]
	for i in range(0,count):
		particles.append(emit_one(speed))
	return particles
		
