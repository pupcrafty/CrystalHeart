extends Node2D

@onready var col_poly: CollisionPolygon2D = $CrystalArea/CrystalShape
@onready var vis_poly: Polygon2D = $CrystalFill
@onready var crystal_points: CrystalPoints = $CrystalPoints

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	set_shape(crystal_points.vertex_points)
	pass # Replace with function body.


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	#set_shape(crystal_points.vertex_points)
	pass

func set_shape(points: PackedVector2Array) -> void:
	# Physics
	col_poly.polygon = points

	# Visual fill
	vis_poly.polygon = points
