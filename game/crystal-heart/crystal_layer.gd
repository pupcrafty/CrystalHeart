extends Node2D
class_name CrystalLayerControl
@export var emit_ready: bool = true
@export var crystalizing: bool = false
@export var fully_crystalized: bool = false
@export var max_previous_shape_overlays: int = 0
@export var shape_colors: Array[Color] = [
	Color(0.92, 0.35, 0.33, 0.85),
	Color(0.18, 0.70, 0.82, 0.85),
	Color(0.95, 0.74, 0.22, 0.85),
	Color(0.41, 0.79, 0.46, 0.85),
	Color(0.85, 0.46, 0.78, 0.85),
	Color(0.98, 0.56, 0.18, 0.85)
]

@onready var col_poly: CollisionPolygon2D = $CrystalArea/CrystalShape
@onready var vis_poly: Polygon2D = $CrystalFill
@onready var crystal_points: CrystalPoints = $CrystalPoints
@onready var emitter_array: EmitterArray = $EmitterArray
@onready var lattice: Lattice = $Lattice
@onready var file_output: FileOutput = get_node_or_null("FileOutput") as FileOutput

var time_till_crystalize: float = 5.0
var crystalization_count_down: float = 5.0
var pending_initial_vertex_points: PackedVector2Array = PackedVector2Array()
var has_pending_initial_vertex_points: bool = false
var previous_shape_container: Node2D
var shape_color_index: int = -1

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	ensure_previous_shape_container()
	vis_poly.z_index = 0
	if has_pending_initial_vertex_points:
		set_shape(pending_initial_vertex_points)
		has_pending_initial_vertex_points = false
	else:
		set_shape(crystal_points.vertex_points)
	crystalization_count_down = time_till_crystalize
	pass # Replace with function body.


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	if crystalizing:
		return
	crystalization_count_down = clampf(crystalization_count_down - delta, 0.0, time_till_crystalize)
	if crystalization_count_down == 0.0:
		crystalization_count_down = time_till_crystalize
		crystalize()
	pass

func set_shape(points: PackedVector2Array, choose_new_color: bool = true) -> void:
	crystal_points.set_vertex_points(points)

	# Physics
	col_poly.polygon = crystal_points.vertex_points

	# Visual fill
	vis_poly.polygon = crystal_points.vertex_points
	if choose_new_color:
		vis_poly.color = get_next_shape_color()
	
	set_up_emitters()
	
func set_up_emitters() -> void:
	emitter_array.emitters.clear()
	for vertex_index in range(0, crystal_points.vertex_points.size()):
		var point: Vector2 = crystal_points.vertex_points[vertex_index]
		var emitter: LiquidEmitter = LiquidEmitter.new()
		emitter.set_position(point)
		emitter.set_emit_angle(get_vertex_half_angle(vertex_index))
		emitter_array.emitters.append(emitter)
	for midpoint_index in range(0, crystal_points.side_mid_points.size()):
		var point: Vector2 = crystal_points.side_mid_points[midpoint_index]
		var emitter: LiquidEmitter = LiquidEmitter.new()
		emitter.set_position(point)
		emitter.set_emit_angle(get_edge_tangent_angle(midpoint_index))
		emitter_array.emitters.append(emitter)

func crystalize() -> void:
	crystalizing = true
	fully_crystalized = false
	lattice.begin_crystalization(crystal_points.vertex_points)


func initialize_with_points(points: PackedVector2Array) -> void:
	pending_initial_vertex_points = points.duplicate()
	has_pending_initial_vertex_points = true
	if is_node_ready():
		set_shape(pending_initial_vertex_points)
		has_pending_initial_vertex_points = false


func handle_crystalization_complete(new_vertex_points: PackedVector2Array) -> void:
	crystalizing = false
	fully_crystalized = true
	var previous_points: PackedVector2Array = crystal_points.vertex_points.duplicate()
	add_previous_shape_overlay(previous_points, vis_poly.color)
	if file_output != null:
		file_output.save_replaced_shape(previous_points, vis_poly.color)
	emitter_array.clear_particles()
	set_shape(new_vertex_points)
	crystalization_count_down = time_till_crystalize


func ensure_previous_shape_container() -> void:
	if previous_shape_container != null:
		return
	previous_shape_container = Node2D.new()
	previous_shape_container.name = "PreviousShapeOverlays"
	previous_shape_container.z_index = 1
	add_child(previous_shape_container)


func add_previous_shape_overlay(points: PackedVector2Array, color: Color) -> void:
	if points.size() < 3:
		return
	ensure_previous_shape_container()
	var previous_shape: Polygon2D = Polygon2D.new()
	previous_shape.polygon = points.duplicate()
	previous_shape.color = color
	previous_shape.z_index = 1
	previous_shape_container.add_child(previous_shape)
	# Draw newer archived shapes first so older ones stay visually on top.
	previous_shape_container.move_child(previous_shape, 0)
	if max_previous_shape_overlays > 0:
		while previous_shape_container.get_child_count() > max_previous_shape_overlays:
			previous_shape_container.get_child(0).queue_free()


func get_next_shape_color() -> Color:
	if shape_colors.is_empty():
		return Color(1.0, 1.0, 1.0, 0.85)
	shape_color_index = (shape_color_index + 1) % shape_colors.size()
	return shape_colors[shape_color_index]


func get_edge_tangent_angle(edge_index: int) -> float:
	var points: PackedVector2Array = crystal_points.vertex_points
	if points.size() < 2:
		return 0.0

	var index_a: int = posmod(edge_index, points.size())
	var index_b: int = (index_a + 1) % points.size()
	var mid_point: Vector2 = (points[index_a] + points[index_b]) * 0.5
	var center: Vector2 = get_polygon_center(points)
	var outward: Vector2 = mid_point - center
	if outward == Vector2.ZERO:
		var edge: Vector2 = points[index_b] - points[index_a]
		if edge == Vector2.ZERO:
			return 0.0
		return edge.angle()
	return outward.angle()


func get_vertex_half_angle(vertex_index: int) -> float:
	var points: PackedVector2Array = crystal_points.vertex_points
	if points.size() == 0:
		return 0.0

	var index_curr: int = posmod(vertex_index, points.size())
	var center: Vector2 = get_polygon_center(points)
	var outward: Vector2 = points[index_curr] - center
	if outward == Vector2.ZERO:
		return points[index_curr].angle()
	return outward.angle()


func get_polygon_center(points: PackedVector2Array) -> Vector2:
	if points.size() == 0:
		return Vector2.ZERO
	var center: Vector2 = Vector2.ZERO
	for point in points:
		center += point
	return center / float(points.size())
