extends RefCounted
class_name WorldLevelDefinition

var level_id: String = ""
var display_name: String = ""
var resource_path: String = ""
var width: int = 0
var height: int = 0
var difficulty: String = ""
var solution_total_steps: int = 0
var order_index: int = 0


func configure(data: Dictionary) -> WorldLevelDefinition:
	level_id = String(data.get("level_id", ""))
	display_name = String(data.get("display_name", ""))
	resource_path = String(data.get("resource_path", ""))
	width = int(data.get("width", 0))
	height = int(data.get("height", 0))
	difficulty = String(data.get("difficulty", ""))
	solution_total_steps = int(data.get("solution_total_steps", 0))
	order_index = int(data.get("order_index", 0))
	return self


func list_label() -> String:
	var board_label := "%dx%d" % [width, height]
	if width <= 0 or height <= 0:
		board_label = "Unknown board"

	var difficulty_label := difficulty.capitalize()
	if difficulty_label.is_empty():
		difficulty_label = "Unknown"

	return "%02d. %s [%s, %s]" % [
		order_index + 1,
		display_name,
		board_label,
		difficulty_label,
	]
