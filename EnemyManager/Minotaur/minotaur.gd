extends "res://EnemyManager/enemy_base.gd"


func _ready() -> void:
	enemy_type = "minotaur"
	super._ready()


func take_turn(player_cell: Vector2i, _occupied_cells: Array[Vector2i]) -> Dictionary:
	var previous_cell: Vector2i = current_cell
	var resolved_turn: Dictionary = _resolve_minotaur_turn(current_cell, player_cell)
	var traversed_cells: Array[Vector2i] = resolved_turn.get("path", [])

	for step_cell in traversed_cells:
		_update_facing(step_cell - current_cell)
		current_cell = step_cell
		await _animate_to_world_position(board_state.to_world(current_cell))

	return {
		"enemy_type": enemy_type,
		"spawn_order": spawn_order,
		"traits": traits.duplicate(),
		"previous_cell": previous_cell,
		"new_cell": current_cell,
		"contact_player": resolved_turn.get("contact_player", false),
		"died": false,
		"killed_spawn_order": -1,
	}


func _resolve_minotaur_turn(current_cell: Vector2i, player_cell: Vector2i) -> Dictionary:
	var resolved_cell: Vector2i = current_cell
	var traversed_cells: Array[Vector2i] = []

	for _step in range(2):
		var next_cell: Vector2i = _choose_minotaur_step(resolved_cell, player_cell)
		if next_cell == resolved_cell:
			continue

		resolved_cell = next_cell
		traversed_cells.append(resolved_cell)
		if resolved_cell == player_cell:
			break

	return {
		"new_cell": resolved_cell,
		"path": traversed_cells,
		"contact_player": resolved_cell == player_cell,
	}


func _choose_minotaur_step(current_cell: Vector2i, player_cell: Vector2i) -> Vector2i:
	if player_cell.x > current_cell.x:
		var right_cell := current_cell + Vector2i.RIGHT
		if board_state.can_enemy_step(current_cell, right_cell):
			return right_cell
	elif player_cell.x < current_cell.x:
		var left_cell := current_cell + Vector2i.LEFT
		if board_state.can_enemy_step(current_cell, left_cell):
			return left_cell

	if player_cell.y < current_cell.y:
		var up_cell := current_cell + Vector2i.UP
		if board_state.can_enemy_step(current_cell, up_cell):
			return up_cell
	elif player_cell.y > current_cell.y:
		var down_cell := current_cell + Vector2i.DOWN
		if board_state.can_enemy_step(current_cell, down_cell):
			return down_cell

	return current_cell
