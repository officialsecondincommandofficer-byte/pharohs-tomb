extends RefCounted
class_name MinotaurSolver


static func solve_board(board: MazeData) -> Dictionary:
	var move_queue: Array[Dictionary] = []
	var initial_player: Vector2i = board.player_spawn
	var initial_minotaur: Vector2i = board.minotaur_spawn

	for option in board.get_move_options(initial_player, true):
		move_queue.append({
			"action": option,
			"player": initial_player,
			"minotaur": initial_minotaur,
			"moves": [],
		})

	var visited: Dictionary = {}

	while not move_queue.is_empty():
		var current: Dictionary = move_queue.pop_front()
		var action: String = String(current["action"])
		var player_cell: Vector2i = current["player"]
		var minotaur_cell: Vector2i = current["minotaur"]
		var visit_key: String = _state_action_key(action, player_cell, minotaur_cell)
		if visited.has(visit_key):
			continue
		visited[visit_key] = true

		var next_player: Vector2i = board.apply_action(player_cell, action)
		if next_player == player_cell and action != "skip":
			continue

		var minotaur_result: Dictionary = resolve_minotaur_turn(minotaur_cell, next_player, board)
		var next_minotaur: Vector2i = minotaur_result["new_cell"]
		if next_minotaur == next_player:
			continue

		var moves: Array[String] = []
		for previous_action in current["moves"]:
			moves.append(String(previous_action))
		moves.append(action)

		if next_player == board.exit_cell:
			return {
				"solvable": true,
				"solution": moves,
			}

		for next_action in board.get_move_options(next_player, true):
			move_queue.append({
				"action": next_action,
				"player": next_player,
				"minotaur": next_minotaur,
				"moves": moves,
			})

	return {
		"solvable": false,
		"solution": [],
	}


static func resolve_minotaur_turn(
	current_cell: Vector2i,
	player_cell: Vector2i,
	board: MazeData
) -> Dictionary:
	var resolved_cell: Vector2i = current_cell
	var traversed_cells: Array[Vector2i] = []

	for _step in range(2):
		var next_cell: Vector2i = _choose_minotaur_step(resolved_cell, player_cell, board)
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


static func _choose_minotaur_step(
	current_cell: Vector2i,
	player_cell: Vector2i,
	board: MazeData
) -> Vector2i:
	if player_cell.x > current_cell.x:
		var right_cell := current_cell + Vector2i.RIGHT
		if board.can_step(current_cell, right_cell):
			return right_cell
	elif player_cell.x < current_cell.x:
		var left_cell := current_cell + Vector2i.LEFT
		if board.can_step(current_cell, left_cell):
			return left_cell

	if player_cell.y < current_cell.y:
		var up_cell := current_cell + Vector2i.UP
		if board.can_step(current_cell, up_cell):
			return up_cell
	elif player_cell.y > current_cell.y:
		var down_cell := current_cell + Vector2i.DOWN
		if board.can_step(current_cell, down_cell):
			return down_cell

	return current_cell


static func _state_action_key(action: String, player_cell: Vector2i, minotaur_cell: Vector2i) -> String:
	return "%s|%d,%d|%d,%d" % [
		action,
		player_cell.x,
		player_cell.y,
		minotaur_cell.x,
		minotaur_cell.y,
	]
