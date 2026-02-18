extends Node
class_name FileOutput

const BASE_OUTPUT_DIR_NAME: String = "crystal_shapes"
const OUTPUT_FILE_NAME: String = "shapes.json"

var current_run_id: String = ""
var current_run_path: String = ""
var shape_index: int = 0
var run_data: Dictionary = {}


func _ready() -> void:
	start_new_run()


func start_new_run() -> void:
	shape_index = 0
	_ensure_base_output_dir()
	current_run_id = _build_unique_run_id()
	_ensure_run_output_dir(current_run_id)
	current_run_path = "user://%s/%s" % [BASE_OUTPUT_DIR_NAME, current_run_id]
	run_data = {
		"run_id": current_run_id,
		"created_unix": Time.get_unix_time_from_system(),
		"shapes": []
	}
	_write_json()


func save_replaced_shape(points: PackedVector2Array, color: Color) -> void:
	if points.size() < 3:
		return
	if current_run_path.is_empty():
		start_new_run()
	shape_index += 1

	var serialized_points: Array[Dictionary] = []
	for point: Vector2 in points:
		serialized_points.append({"x": point.x, "y": point.y})

	var shapes: Array = run_data.get("shapes", [])
	shapes.append({
		"index": shape_index,
		"saved_unix": Time.get_unix_time_from_system(),
		"color": {
			"r": color.r,
			"g": color.g,
			"b": color.b,
			"a": color.a
		},
		"points": serialized_points
	})
	run_data["shapes"] = shapes
	_write_json()


func _ensure_base_output_dir() -> void:
	var user_dir: DirAccess = DirAccess.open("user://")
	if user_dir == null:
		push_error("FileOutput: Unable to open user://")
		return
	if not user_dir.dir_exists(BASE_OUTPUT_DIR_NAME):
		var result: int = user_dir.make_dir_recursive(BASE_OUTPUT_DIR_NAME)
		if result != OK:
			push_error("FileOutput: Failed to create user://%s (error %d)" % [BASE_OUTPUT_DIR_NAME, result])


func _ensure_run_output_dir(run_id: String) -> void:
	var crystal_shapes_dir: DirAccess = DirAccess.open("user://%s" % BASE_OUTPUT_DIR_NAME)
	if crystal_shapes_dir == null:
		push_error("FileOutput: Unable to open user://%s" % BASE_OUTPUT_DIR_NAME)
		return
	if not crystal_shapes_dir.dir_exists(run_id):
		var result: int = crystal_shapes_dir.make_dir(run_id)
		if result != OK:
			push_error("FileOutput: Failed to create run directory %s (error %d)" % [run_id, result])


func _build_unique_run_id() -> String:
	var unix_time: int = Time.get_unix_time_from_system()
	var ticks: int = Time.get_ticks_msec()
	var candidate: String = "run_%d_%d" % [unix_time, ticks]
	var crystal_shapes_dir: DirAccess = DirAccess.open("user://%s" % BASE_OUTPUT_DIR_NAME)
	if crystal_shapes_dir == null:
		return candidate
	var suffix: int = 1
	while crystal_shapes_dir.dir_exists(candidate):
		candidate = "run_%d_%d_%d" % [unix_time, ticks, suffix]
		suffix += 1
	return candidate


func _write_json() -> void:
	if current_run_path.is_empty():
		return
	var output_path: String = "%s/%s" % [current_run_path, OUTPUT_FILE_NAME]
	var output_file: FileAccess = FileAccess.open(output_path, FileAccess.WRITE)
	if output_file == null:
		push_error("FileOutput: Unable to write %s" % output_path)
		return
	output_file.store_string(JSON.stringify(run_data, "\t"))
	output_file.close()
