extends Node2D
class_name Lattice

var slots_available_per_particle: Array[int] = [2,3,4,5,6]
@export var slots: int 

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	pass # Replace with function body.


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	pass

func begin_crystalization(corners: Array[Vector2])->void:
	slots = slots_available_per_particle.pick_random()
	print("Slots chosen: ",slots)
	var perimeter: float = calculate_perimeter(corners)
	print("Perimeter =", perimeter)
	pass


func calculate_perimeter(corners:Array[Vector2]) -> float:
	var total_perimeter: float = 0
	for i in range(0, corners.size()):
		if i+2 <= corners.size():
			total_perimeter+=(corners[i]-corners[i+1]).length()
		else:
			total_perimeter+=(corners[i]-corners[0]).length()
	return total_perimeter
