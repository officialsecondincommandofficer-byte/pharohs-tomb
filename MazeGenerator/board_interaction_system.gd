extends RefCounted
class_name BoardInteractionSystem


const ACTOR_PLAYER := "player"
const ACTOR_ENEMY := "enemy"


static func can_step(board, a: Vector2i, b: Vector2i, actor: String = ACTOR_PLAYER) -> bool:
	if not board.is_in_bounds(a) or not board.is_in_bounds(b):
		return false
	return not is_blocked(board, a, b, actor)


static func is_blocked(board, a: Vector2i, b: Vector2i, actor: String = ACTOR_PLAYER) -> bool:
	var delta: Vector2i = b - a
	if abs(delta.x) + abs(delta.y) != 1:
		return true
	if has_shared_wall_between(board, a, b):
		return true

	if actor == ACTOR_ENEMY:
		if delta.x != 0:
			return board.has_player_vertical_wall(Vector2i(max(a.x, b.x), a.y)) or board.has_one_way_passage(b, a)
		return board.has_player_horizontal_wall(Vector2i(a.x, max(a.y, b.y))) or board.has_one_way_passage(b, a)

	if delta.x != 0:
		return board.has_enemy_vertical_wall(Vector2i(max(a.x, b.x), a.y)) or board.has_one_way_passage(b, a)
	return board.has_enemy_horizontal_wall(Vector2i(a.x, max(a.y, b.y))) or board.has_one_way_passage(b, a)


static func has_shared_wall_between(board, a: Vector2i, b: Vector2i) -> bool:
	var delta: Vector2i = b - a
	if abs(delta.x) + abs(delta.y) != 1:
		return true
	if delta.x != 0:
		return board.has_vertical_wall(Vector2i(max(a.x, b.x), a.y))
	return board.has_horizontal_wall(Vector2i(a.x, max(a.y, b.y)))


static func apply_cardinal_action(board, cell: Vector2i, action: String, actor: String = ACTOR_PLAYER) -> Vector2i:
	if action == "skip":
		return cell
	if not board.ACTION_TO_DIRECTION.has(action):
		return cell
	var next_cell: Vector2i = cell + board.ACTION_TO_DIRECTION[action]
	if not can_step(board, cell, next_cell, actor):
		return cell
	return next_cell


static func resolve_player_transition(board, cell: Vector2i, action: String) -> Dictionary:
	var stepped_cell: Vector2i = apply_cardinal_action(board, cell, action, ACTOR_PLAYER)
	var resolved_cell: Vector2i = teleport_destination(board, stepped_cell, ACTOR_PLAYER, false)
	return {
		"stepped_cell": stepped_cell,
		"resolved_cell": resolved_cell,
		"used_teleport": resolved_cell != stepped_cell,
	}


static func resolve_turn_end_transition(board, final_cell: Vector2i, actor: String) -> Dictionary:
	var resolved_cell: Vector2i = final_cell
	if actor == ACTOR_ENEMY:
		resolved_cell = teleport_destination(board, final_cell, ACTOR_ENEMY, true, true)
	else:
		resolved_cell = teleport_destination(board, final_cell, ACTOR_PLAYER, true, true)
	return {
		"stepped_cell": final_cell,
		"resolved_cell": resolved_cell,
		"used_teleport": resolved_cell != final_cell,
	}


static func teleport_destination(
	board,
	cell: Vector2i,
	actor: String = ACTOR_PLAYER,
	turn_end_only: bool = false,
	include_shared: bool = true
) -> Vector2i:
	if actor == ACTOR_PLAYER:
		if not turn_end_only and board._teleport_lookup.has(cell):
			return board._teleport_lookup[cell]
		if include_shared and board._shared_teleport_lookup.has(cell):
			return board._shared_teleport_lookup[cell]
		return cell

	if board._enemy_teleport_lookup.has(cell):
		return board._enemy_teleport_lookup[cell]
	if include_shared and board._shared_teleport_lookup.has(cell):
		return board._shared_teleport_lookup[cell]
	return cell


static func cardinal_neighbors(board, cell: Vector2i, actor: String = ACTOR_PLAYER) -> Array[Vector2i]:
	var neighbors: Array[Vector2i] = []
	for direction in board.ACTION_TO_DIRECTION.values():
		var next_cell: Vector2i = cell + direction
		if can_step(board, cell, next_cell, actor):
			neighbors.append(next_cell)
	return neighbors


static func is_trap_cell(board, cell: Vector2i) -> bool:
	return board._trap_lookup.has(cell)
