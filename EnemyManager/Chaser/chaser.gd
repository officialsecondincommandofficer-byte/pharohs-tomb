extends "res://EnemyManager/enemy_base.gd"

var move_priority: String = "horizontal"


func _ready() -> void:
	enemy_type = "chaser"
	super._ready()


func configure(spawn_data: Dictionary, next_board_state) -> void:
	move_priority = String(spawn_data.get("move_priority", "horizontal"))
	super.configure(spawn_data, next_board_state)


func take_turn(player_cell: Vector2i, occupied_cells: Array[Vector2i]) -> Dictionary:
	var occupied_lookup: Dictionary = {}
	for cell in occupied_cells:
		if cell != current_cell:
			occupied_lookup[cell] = true

	var previous_cell: Vector2i = current_cell

	for _step in 2:
		var next_cell: Vector2i = _choose_greedy_step(player_cell, occupied_lookup)
		if next_cell == current_cell:
			continue

		var step_direction: Vector2i = next_cell - current_cell
		current_cell = next_cell
		_update_facing(step_direction)
		await _animate_to_world_position(board_state.to_world(current_cell))
		if current_cell == player_cell:
			break

	var result: Dictionary = {
		"enemy_type": enemy_type,
		"previous_cell": previous_cell,
		"new_cell": current_cell,
		"contact_player": current_cell == player_cell,
	}

	return result


func _choose_greedy_step(player_cell: Vector2i, occupied_lookup: Dictionary) -> Vector2i:
	var vertical_direction: int = sign(player_cell.y - current_cell.y)
	var horizontal_direction: int = sign(player_cell.x - current_cell.x)
	var preferred_axes: Array[String] = ["horizontal", "vertical"]

	if move_priority == "vertical":
		preferred_axes = ["vertical", "horizontal"]

	for axis in preferred_axes:
		if axis == "vertical" and vertical_direction != 0:
			var vertical_target: Vector2i = current_cell + Vector2i(0, vertical_direction)
			if _can_enter(vertical_target, occupied_lookup):
				return vertical_target

		if axis == "horizontal" and horizontal_direction != 0:
			var horizontal_target: Vector2i = current_cell + Vector2i(horizontal_direction, 0)
			if _can_enter(horizontal_target, occupied_lookup):
				return horizontal_target

	return current_cell
