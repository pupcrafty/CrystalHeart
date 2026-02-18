class_name LiquidEmitter

var pos: Vector2
var emit_angle: float
var size: float = 5.0
# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	pass # Replace with function body.

func emit_one(speed: float) -> FluidParticle:

	var p: FluidParticle = FluidParticle.new()
	p.pos = pos
	p.vel = Vector2.from_angle(emit_angle) * speed
	return p

func set_position(in_pos: Vector2) -> void:
	pos = in_pos

func set_emit_angle(angle: float) -> void:
	emit_angle = angle

func emit_many(count: int, speed: float) -> Array[FluidParticle]:
	var particles: Array[FluidParticle] = []
	for _i: int in range(0, count):
		particles.append(emit_one(speed))
	return particles
