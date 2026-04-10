extends "res://EnemyManager/enemy_base.gd"

const SolverScript = preload("res://MazeGenerator/Core/minotaur_solver.gd")


func _ready() -> void:
	enemy_type = "minotaur"
	super._ready()


func take_turn(player_cell: Vector2i, _occupied_cells: Array[Vector2i]) -> Dictionary:
	var previous_cell: Vector2i = current_cell
	var resolved_turn: Dictionary = SolverScript.resolve_minotaur_turn(current_cell, player_cell, board_state)
	var traversed_cells: Array[Vector2i] = resolved_turn.get("path", [])

	for step_cell in traversed_cells:
		_update_facing(step_cell - current_cell)
		current_cell = step_cell
		await _animate_to_world_position(board_state.to_world(current_cell))

	return {
		"enemy_type": enemy_type,
		"previous_cell": previous_cell,
		"new_cell": current_cell,
		"contact_player": resolved_turn.get("contact_player", false),
	}
