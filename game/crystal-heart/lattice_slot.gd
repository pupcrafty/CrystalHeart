class_name LatticeSlot

var pos: Vector2
var dir: Vector2
var filled: bool = false

func _init(in_pos: Vector2, in_dir: Vector2, in_filled: bool = false) -> void:
	pos = in_pos
	dir = in_dir
	filled = in_filled
