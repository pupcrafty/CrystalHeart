extends Node2D
class_name CrystalLayerControl
@export var emit_ready: bool = true
@export var crystalizing: bool = false
@export var fully_crystalized: bool = false
@export var crystal_layer_scene: PackedScene

@onready var col_poly: CollisionPolygon2D = $CrystalArea/CrystalShape
@onready var vis_poly: Polygon2D = $CrystalFill
@onready var crystal_points: CrystalPoints = $CrystalPoints
@onready var emitter_array: EmitterArray = $EmitterArray
@onready var lattice: Lattice = $Lattice

const DEFAULT_CRYSTAL_LAYER_SCENE_PATH: String = "res://crystal_layer.tscn"

var time_till_crystalize: float = 5.0
var crystalization_count_down: float = 5.0
var pending_initial_vertex_points: PackedVector2Array = PackedVector2Array()
var has_pending_initial_vertex_points: bool = false

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
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

func set_shape(points: PackedVector2Array) -> void:
	crystal_points.set_vertex_points(points)

	# Physics
	col_poly.polygon = crystal_points.vertex_points

	# Visual fill
	vis_poly.polygon = crystal_points.vertex_points
	
	set_up_emitters()
	
func set_up_emitters() -> void:
	emitter_array.emitters.clear()
	for point in crystal_points.vertex_points:
		var emitter: LiquidEmitter = LiquidEmitter.new()
		emitter.set_position(point)
		emitter.set_emit_angle(point.angle())
		emitter_array.emitters.append(emitter)
	for point in crystal_points.side_mid_points:
		var emitter: LiquidEmitter = LiquidEmitter.new()
		emitter.set_position(point)
		emitter.set_emit_angle(point.angle())
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
	emitter_array.clear_particles()
	spawn_next_crystal_layer(new_vertex_points)


func spawn_next_crystal_layer(points: PackedVector2Array) -> void:
	var parent_node: Node = get_parent()
	if parent_node == null:
		return

	var layer_scene: PackedScene = crystal_layer_scene
	if layer_scene == null:
		layer_scene = load(DEFAULT_CRYSTAL_LAYER_SCENE_PATH) as PackedScene
	if layer_scene == null:
		push_error("CrystalLayer scene missing; applying points to current layer instead.")
		set_shape(points)
		return

	var next_layer: CrystalLayerControl = layer_scene.instantiate() as CrystalLayerControl
	if next_layer == null:
		push_error("Could not instantiate CrystalLayer scene.")
		set_shape(points)
		return

	parent_node.add_child(next_layer)
	next_layer.global_position = global_position
	next_layer.initialize_with_points(points)
	queue_free()
