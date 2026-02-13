extends Node
class_name CrystalPoints

@export var vertex_points: PackedVector2Array
@export var side_mid_points: PackedVector2Array

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	set_mid_points()
	pass


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	pass

func set_mid_points() -> void:
	if vertex_points.size() > 3:
		side_mid_points = PackedVector2Array()
		for vertex_index in range(0, vertex_points.size()):
			if vertex_index < vertex_points.size() - 1:
				var mid_point: Vector2 = get_mid_point(vertex_points.get(vertex_index), vertex_points.get(vertex_index + 1))
				side_mid_points.append(mid_point)
			else:
				var mid_point: Vector2 = get_mid_point(vertex_points.get(vertex_index), vertex_points.get(0))
				side_mid_points.append(mid_point)

func get_mid_point(point_a: Vector2, point_b: Vector2) -> Vector2:
	var mid_x: float = (point_a.x + point_b.x) / 2.0
	var mid_y: float = (point_a.y + point_b.y) / 2.0
	return Vector2(mid_x, mid_y)

func print_mid_points() -> void:
	for mid_point in side_mid_points:
		print("Mid-point: x=", mid_point.x, ", y=", mid_point.y)
