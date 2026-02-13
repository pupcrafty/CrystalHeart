extends Node2D
class_name CrystalLayerControl
@export var emit_ready = true
@export var crystalizing = false

@onready var col_poly: CollisionPolygon2D = $CrystalArea/CrystalShape
@onready var vis_poly: Polygon2D = $CrystalFill
@onready var crystal_points: CrystalPoints = $CrystalPoints
@onready var emitter_array: EmitterArray = $EmitterArray


# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	set_shape(crystal_points.vertex_points)
	pass # Replace with function body.


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	pass

func set_shape(points: PackedVector2Array) -> void:
	# Physics
	col_poly.polygon = points

	# Visual fill
	vis_poly.polygon = points
	
	set_up_emitters()
	
func set_up_emitters()->void:
	for point in crystal_points.vertex_points:
		var emitter = LiquidEmitter.new()
		emitter.set_position(point)
		emitter.set_emit_angle(point.angle())
		emitter_array.emitters.append(emitter)
	for point in crystal_points.side_mid_points:
		var emitter = LiquidEmitter.new()
		emitter.set_position(point)
		emitter.set_emit_angle(point.angle())
		emitter_array.emitters.append(emitter)
		
