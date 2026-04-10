extends RefCounted
class_name ChaserLogic


static func choose_greedy_step(
	current_cell: Vector2i,
	player_cell: Vector2i,
	occupied_lookup: Dictionary,
	board_state,
	move_priority: String = "horizontal"
) -> Vector2i:
	var vertical_direction: int = sign(player_cell.y - current_cell.y)
	var horizontal_direction: int = sign(player_cell.x - current_cell.x)
	var preferred_axes: Array[String] = ["horizontal", "vertical"]

	if move_priority == "vertical":
		preferred_axes = ["vertical", "horizontal"]

	for axis in preferred_axes:
		if axis == "vertical" and vertical_direction != 0:
			var vertical_target: Vector2i = current_cell + Vector2i(0, vertical_direction)
			if _can_enter(current_cell, vertical_target, occupied_lookup, board_state):
				return vertical_target

		if axis == "horizontal" and horizontal_direction != 0:
			var horizontal_target: Vector2i = current_cell + Vector2i(horizontal_direction, 0)
			if _can_enter(current_cell, horizontal_target, occupied_lookup, board_state):
				return horizontal_target

	return current_cell


static func resolve_turn(
	current_cell: Vector2i,
	player_cell: Vector2i,
	occupied_cells: Array[Vector2i],
	board_state,
	move_priority: String = "horizontal",
	step_count: int = 2
) -> Dictionary:
	var occupied_lookup: Dictionary = {}
	for cell in occupied_cells:
		if cell != current_cell:
			occupied_lookup[cell] = true

	var resolved_cell: Vector2i = current_cell
	for _step in step_count:
		var next_cell: Vector2i = choose_greedy_step(
			resolved_cell,
			player_cell,
			occupied_lookup,
			board_state,
			move_priority
		)
		if next_cell == resolved_cell:
			continue
		resolved_cell = next_cell
		if resolved_cell == player_cell:
			break

	return {
		"new_cell": resolved_cell,
		"contact_player": resolved_cell == player_cell,
	}


static func _can_enter(
	current_cell: Vector2i,
	target_cell: Vector2i,
	occupied_lookup: Dictionary,
	board_state
) -> bool:
	if not board_state.can_step(current_cell, target_cell):
		return false
	return not occupied_lookup.has(target_cell)
