extends RefCounted
class_name AStarChaserLogic


static func choose_astar_step(
	current_cell: Vector2i,
	player_cell: Vector2i,
	occupied_lookup: Dictionary,
	board_state
) -> Vector2i:
	var path: Array[Vector2i] = _find_astar_path(current_cell, player_cell, occupied_lookup, board_state)
	if path.size() < 2:
		return current_cell
	return path[1]


static func _find_astar_path(
	start: Vector2i,
	goal: Vector2i,
	occupied_lookup: Dictionary,
	board_state
) -> Array[Vector2i]:
	var frontier: Array[Dictionary] = [{"cell": start, "cost": 0, "priority": _manhattan_distance(start, goal)}]
	var came_from: Dictionary = {start: start}
	var cost_so_far: Dictionary = {start: 0}

	while not frontier.is_empty():
		frontier.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
			return int(a.get("priority", 0)) < int(b.get("priority", 0))
		)
		var current: Vector2i = frontier.pop_front().get("cell", start)
		if current == goal:
			break

		for neighbor in board_state.get_enemy_cardinal_neighbors(current):
			if occupied_lookup.has(neighbor) and neighbor != goal:
				continue
			var next_cost: int = int(cost_so_far.get(current, 0)) + 1
			if cost_so_far.has(neighbor) and next_cost >= int(cost_so_far[neighbor]):
				continue
			cost_so_far[neighbor] = next_cost
			came_from[neighbor] = current
			frontier.append({
				"cell": neighbor,
				"cost": next_cost,
				"priority": next_cost + _manhattan_distance(neighbor, goal),
			})

	if not came_from.has(goal):
		return [start]

	var path: Array[Vector2i] = [goal]
	var cursor := goal
	while cursor != start:
		cursor = came_from[cursor]
		path.push_front(cursor)
	return path


static func _manhattan_distance(a: Vector2i, b: Vector2i) -> int:
	return absi(a.x - b.x) + absi(a.y - b.y)
