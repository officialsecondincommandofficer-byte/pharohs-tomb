extends RefCounted
class_name MazeData

const EnemySpawnDataScript = preload("res://MazeGenerator/enemy_spawn_data.gd")
const BoardInteractionSystemScript = preload("res://MazeGenerator/board_interaction_system.gd")

const SAVE_VERSION := 1

const ACTION_TO_DIRECTION := {
	"left": Vector2i.LEFT,
	"right": Vector2i.RIGHT,
	"up": Vector2i.UP,
	"down": Vector2i.DOWN,
}

var width: int = 0
var height: int = 0
var cell_size: int = 16
var wall_density: float = 0.0
var size_category: String = "small"
var difficulty_category: String = "easy"
var floor_cells: Array[Vector2i] = []
var wall_cells: Array[Vector2i] = []
var horizontal_walls: Array[Vector2i] = []
var vertical_walls: Array[Vector2i] = []
var player_horizontal_walls: Array[Vector2i] = []
var player_vertical_walls: Array[Vector2i] = []
var enemy_horizontal_walls: Array[Vector2i] = []
var enemy_vertical_walls: Array[Vector2i] = []
var one_way_passages: Array[Dictionary] = []
var teleport_pairs: Array[Dictionary] = []
var enemy_teleport_pairs: Array[Dictionary] = []
var shared_teleport_pairs: Array[Dictionary] = []
var trap_cells: Array[Vector2i] = []
var player_spawn: Vector2i = Vector2i.ZERO
var enemy_spawns: Array[Dictionary] = []
var minotaur_spawn: Vector2i = Vector2i.ZERO
var exit_cell: Vector2i = Vector2i.ZERO
var exit_cells: Array[Vector2i] = []
var escape_zone_cells: Array[Vector2i] = []
var zone_spawners: Array[Dictionary] = []
var solution_actions: Array[String] = []
var solution_total_steps: int = 0
var maze_key: Dictionary = {}
var generation_mode: String = "RUNTIME_GENERATED"
var generation_profile_id: String = ""
var display_name: String = ""
var saved_at_unix: int = 0

var _floor_lookup: Dictionary = {}
var _horizontal_wall_lookup: Dictionary = {}
var _vertical_wall_lookup: Dictionary = {}
var _player_horizontal_wall_lookup: Dictionary = {}
var _player_vertical_wall_lookup: Dictionary = {}
var _enemy_horizontal_wall_lookup: Dictionary = {}
var _enemy_vertical_wall_lookup: Dictionary = {}
var _one_way_passage_lookup: Dictionary = {}
var _teleport_lookup: Dictionary = {}
var _enemy_teleport_lookup: Dictionary = {}
var _shared_teleport_lookup: Dictionary = {}
var _trap_lookup: Dictionary = {}
var _exit_lookup: Dictionary = {}
var _escape_zone_lookup: Dictionary = {}


func configure_from_maze_key(
	next_maze_key: Dictionary,
	next_cell_size: int,
	next_size_category: String,
	next_difficulty_category: String
) -> void:
	width = int(_coerce_vector2i(next_maze_key.get("size_board", Vector2i.ONE)).x)
	height = int(_coerce_vector2i(next_maze_key.get("size_board", Vector2i.ONE)).y)
	cell_size = next_cell_size
	size_category = next_size_category
	difficulty_category = next_difficulty_category
	maze_key = next_maze_key.duplicate(true)
	floor_cells.clear()
	wall_cells.clear()
	horizontal_walls.clear()
	vertical_walls.clear()
	player_horizontal_walls.clear()
	player_vertical_walls.clear()
	enemy_horizontal_walls.clear()
	enemy_vertical_walls.clear()
	one_way_passages.clear()
	teleport_pairs.clear()
	enemy_teleport_pairs.clear()
	shared_teleport_pairs.clear()
	trap_cells.clear()
	enemy_spawns.clear()
	exit_cells.clear()
	escape_zone_cells.clear()
	zone_spawners.clear()
	solution_actions.clear()
	_floor_lookup.clear()
	_horizontal_wall_lookup.clear()
	_vertical_wall_lookup.clear()
	_player_horizontal_wall_lookup.clear()
	_player_vertical_wall_lookup.clear()
	_enemy_horizontal_wall_lookup.clear()
	_enemy_vertical_wall_lookup.clear()
	_one_way_passage_lookup.clear()
	_teleport_lookup.clear()
	_enemy_teleport_lookup.clear()
	_shared_teleport_lookup.clear()
	_trap_lookup.clear()
	_exit_lookup.clear()
	_escape_zone_lookup.clear()

	for y in range(height):
		for x in range(width):
			add_floor_cell(Vector2i(x, y))

	for raw_wall in next_maze_key.get("walls", []):
		_add_wall_from_edge(raw_wall)
	for raw_wall in next_maze_key.get("player_only_walls", []):
		_add_wall_from_edge(raw_wall, "player")
	for raw_wall in next_maze_key.get("enemy_only_walls", []):
		_add_wall_from_edge(raw_wall, "enemy")
	for raw_passage in next_maze_key.get("one_way_passages", []):
		add_one_way_passage(raw_passage)
	for raw_teleport_pair in next_maze_key.get("teleport_pairs", []):
		add_teleport_pair(raw_teleport_pair)
	for raw_enemy_teleport_pair in next_maze_key.get("enemy_teleport_pairs", []):
		add_enemy_teleport_pair(raw_enemy_teleport_pair)
	for raw_shared_teleport_pair in next_maze_key.get("shared_teleport_pairs", []):
		add_shared_teleport_pair(raw_shared_teleport_pair)

	player_spawn = _coerce_vector2i(next_maze_key.get("player_start", Vector2i.ZERO))
	minotaur_spawn = _coerce_vector2i(next_maze_key.get("mino_start", Vector2i.ZERO))
	enemy_spawns = EnemySpawnDataScript.coerce_enemy_spawn_array(next_maze_key.get("enemy_spawns", []), minotaur_spawn)
	minotaur_spawn = EnemySpawnDataScript.first_enemy_cell(enemy_spawns, minotaur_spawn)
	exit_cell = _resolve_main_exit_cell_from_payload(next_maze_key, "main_exit_cell", "goal")
	var raw_goal_cells = _resolve_main_exit_cells_from_payload(next_maze_key, "main_exit_cells", "goal_cells", exit_cell)
	if raw_goal_cells.is_empty():
		raw_goal_cells = [exit_cell]
	for raw_exit_cell in raw_goal_cells:
		add_exit_cell(_coerce_vector2i(raw_exit_cell))
	for raw_escape_zone_cell in next_maze_key.get("escape_zone_cells", []):
		add_escape_zone_cell(_coerce_vector2i(raw_escape_zone_cell))
	zone_spawners = _coerce_dictionary_array(next_maze_key.get("escape_zone_spawners", next_maze_key.get("zone_spawners", [])))
	for trap_cell in next_maze_key.get("trap_cells", []):
		add_trap_cell(_coerce_vector2i(trap_cell))

	for action in next_maze_key.get("solution", []):
		solution_actions.append(String(action))

	solution_total_steps = int(next_maze_key.get("sol_length", solution_actions.size()))
	wall_density = float(horizontal_walls.size() + vertical_walls.size()) / max(float(_edge_count()), 1.0)


func to_world(cell: Vector2i) -> Vector2:
	return Vector2(
		cell.x * cell_size + cell_size / 2.0,
		cell.y * cell_size + cell_size / 2.0
	)


func to_map(world_position: Vector2) -> Vector2i:
	return Vector2i(
		int(floor(world_position.x / cell_size)),
		int(floor(world_position.y / cell_size))
	)


func is_in_bounds(cell: Vector2i) -> bool:
	return cell.x >= 0 and cell.y >= 0 and cell.x < width and cell.y < height


func is_walkable(cell: Vector2i) -> bool:
	return _floor_lookup.has(cell)


func add_floor_cell(cell: Vector2i) -> void:
	if _floor_lookup.has(cell):
		return
	floor_cells.append(cell)
	_floor_lookup[cell] = true


func add_horizontal_wall(edge: Vector2i) -> void:
	if _horizontal_wall_lookup.has(edge):
		return
	horizontal_walls.append(edge)
	_horizontal_wall_lookup[edge] = true


func add_vertical_wall(edge: Vector2i) -> void:
	if _vertical_wall_lookup.has(edge):
		return
	vertical_walls.append(edge)
	_vertical_wall_lookup[edge] = true


func add_trap_cell(cell: Vector2i) -> void:
	if not is_in_bounds(cell):
		return
	if _trap_lookup.has(cell):
		return
	trap_cells.append(cell)
	_trap_lookup[cell] = true


func add_exit_cell(cell: Vector2i) -> void:
	if not is_in_bounds(cell):
		return
	if _exit_lookup.has(cell):
		return
	exit_cells.append(cell)
	_exit_lookup[cell] = true


func add_escape_zone_cell(cell: Vector2i) -> void:
	if not is_in_bounds(cell):
		return
	if _escape_zone_lookup.has(cell):
		return
	escape_zone_cells.append(cell)
	_escape_zone_lookup[cell] = true


func add_player_horizontal_wall(edge: Vector2i) -> void:
	if _player_horizontal_wall_lookup.has(edge):
		return
	player_horizontal_walls.append(edge)
	_player_horizontal_wall_lookup[edge] = true


func add_player_vertical_wall(edge: Vector2i) -> void:
	if _player_vertical_wall_lookup.has(edge):
		return
	player_vertical_walls.append(edge)
	_player_vertical_wall_lookup[edge] = true


func add_enemy_horizontal_wall(edge: Vector2i) -> void:
	if _enemy_horizontal_wall_lookup.has(edge):
		return
	enemy_horizontal_walls.append(edge)
	_enemy_horizontal_wall_lookup[edge] = true


func add_enemy_vertical_wall(edge: Vector2i) -> void:
	if _enemy_vertical_wall_lookup.has(edge):
		return
	enemy_vertical_walls.append(edge)
	_enemy_vertical_wall_lookup[edge] = true


func add_one_way_passage(raw_passage) -> void:
	if not raw_passage is Dictionary:
		return

	var from_cell: Vector2i = _coerce_vector2i(raw_passage.get("from", Vector2i.ZERO))
	var to_cell: Vector2i = _coerce_vector2i(raw_passage.get("to", Vector2i.ZERO))
	var delta := to_cell - from_cell
	if abs(delta.x) + abs(delta.y) != 1:
		return
	if not is_in_bounds(from_cell) or not is_in_bounds(to_cell):
		return

	var forward_key := _directed_edge_key(from_cell, to_cell)
	var reverse_key := _directed_edge_key(to_cell, from_cell)
	if _one_way_passage_lookup.has(forward_key) or _one_way_passage_lookup.has(reverse_key):
		return

	var passage := {
		"from": from_cell,
		"to": to_cell,
	}
	one_way_passages.append(passage)
	_one_way_passage_lookup[forward_key] = true


func add_teleport_pair(raw_pair) -> void:
	if not raw_pair is Dictionary:
		return

	var a: Vector2i = _coerce_vector2i(raw_pair.get("a", Vector2i.ZERO))
	var b: Vector2i = _coerce_vector2i(raw_pair.get("b", Vector2i.ZERO))
	if a == b:
		return
	if not is_in_bounds(a) or not is_in_bounds(b):
		return
	if _teleport_lookup.has(a) or _teleport_lookup.has(b):
		return

	var pair := {
		"a": a,
		"b": b,
	}
	teleport_pairs.append(pair)
	_teleport_lookup[a] = b
	_teleport_lookup[b] = a


func add_enemy_teleport_pair(raw_pair) -> void:
	if not raw_pair is Dictionary:
		return

	var a: Vector2i = _coerce_vector2i(raw_pair.get("a", Vector2i.ZERO))
	var b: Vector2i = _coerce_vector2i(raw_pair.get("b", Vector2i.ZERO))
	if a == b:
		return
	if not is_in_bounds(a) or not is_in_bounds(b):
		return
	if _enemy_teleport_lookup.has(a) or _enemy_teleport_lookup.has(b):
		return

	var pair := {
		"a": a,
		"b": b,
	}
	enemy_teleport_pairs.append(pair)
	_enemy_teleport_lookup[a] = b
	_enemy_teleport_lookup[b] = a


func add_shared_teleport_pair(raw_pair) -> void:
	if not raw_pair is Dictionary:
		return

	var a: Vector2i = _coerce_vector2i(raw_pair.get("a", Vector2i.ZERO))
	var b: Vector2i = _coerce_vector2i(raw_pair.get("b", Vector2i.ZERO))
	if a == b:
		return
	if not is_in_bounds(a) or not is_in_bounds(b):
		return
	if _shared_teleport_lookup.has(a) or _shared_teleport_lookup.has(b):
		return

	var pair := {
		"a": a,
		"b": b,
	}
	shared_teleport_pairs.append(pair)
	_shared_teleport_lookup[a] = b
	_shared_teleport_lookup[b] = a


func has_horizontal_wall(edge: Vector2i) -> bool:
	return _horizontal_wall_lookup.has(edge)


func has_vertical_wall(edge: Vector2i) -> bool:
	return _vertical_wall_lookup.has(edge)


func has_player_horizontal_wall(edge: Vector2i) -> bool:
	return _player_horizontal_wall_lookup.has(edge)


func has_player_vertical_wall(edge: Vector2i) -> bool:
	return _player_vertical_wall_lookup.has(edge)


func has_enemy_horizontal_wall(edge: Vector2i) -> bool:
	return _enemy_horizontal_wall_lookup.has(edge)


func has_enemy_vertical_wall(edge: Vector2i) -> bool:
	return _enemy_vertical_wall_lookup.has(edge)


func has_one_way_passage(a: Vector2i, b: Vector2i) -> bool:
	return _one_way_passage_lookup.has(_directed_edge_key(a, b))


func is_trap_cell(cell: Vector2i) -> bool:
	return BoardInteractionSystemScript.is_trap_cell(self, cell)


func is_exit_cell(cell: Vector2i) -> bool:
	return is_win_cell(cell)


func is_main_exit_cell(cell: Vector2i) -> bool:
	return _exit_lookup.has(cell)


func is_win_cell(cell: Vector2i) -> bool:
	return _exit_lookup.has(cell) or _escape_zone_lookup.has(cell)


func is_escape_zone_cell(cell: Vector2i) -> bool:
	return _escape_zone_lookup.has(cell)


func get_main_exit_cell() -> Vector2i:
	return exit_cell


func get_main_exit_cells() -> Array[Vector2i]:
	if exit_cells.is_empty():
		return [exit_cell]
	return exit_cells.duplicate()


func get_win_zone_cells() -> Array[Vector2i]:
	var win_cells: Array[Vector2i] = get_main_exit_cells()
	for escape_zone_cell in escape_zone_cells:
		if not win_cells.has(escape_zone_cell):
			win_cells.append(escape_zone_cell)
	return win_cells


func get_escape_zone_spawners() -> Array[Dictionary]:
	return zone_spawners.duplicate(true)


func goal_distance_from_player_cell(start_cell: Vector2i) -> int:
	if is_win_cell(start_cell):
		return 0
	var queue: Array[Vector2i] = [start_cell]
	var distances: Dictionary = {start_cell: 0}
	while not queue.is_empty():
		var current: Vector2i = queue.pop_front()
		var next_distance: int = int(distances[current]) + 1
		for action in ["right", "left", "up", "down"]:
			var next_cell: Vector2i = apply_action(current, action)
			if next_cell == current or distances.has(next_cell):
				continue
			if is_win_cell(next_cell):
				return next_distance
			distances[next_cell] = next_distance
			queue.append(next_cell)
	return -1


func get_teleport_destination(cell: Vector2i) -> Vector2i:
	return BoardInteractionSystemScript.teleport_destination(self, cell, BoardInteractionSystemScript.ACTOR_PLAYER, false)


func get_enemy_teleport_destination(cell: Vector2i) -> Vector2i:
	return BoardInteractionSystemScript.teleport_destination(self, cell, BoardInteractionSystemScript.ACTOR_ENEMY, true, false)


func get_shared_teleport_destination(cell: Vector2i) -> Vector2i:
	if _shared_teleport_lookup.has(cell):
		return _shared_teleport_lookup[cell]
	return cell


func resolve_player_transition(cell: Vector2i, action: String) -> Dictionary:
	return BoardInteractionSystemScript.resolve_player_transition(self, cell, action)


func resolve_enemy_turn_end_transition(final_cell: Vector2i) -> Dictionary:
	return BoardInteractionSystemScript.resolve_turn_end_transition(self, final_cell, BoardInteractionSystemScript.ACTOR_ENEMY)


func resolve_player_turn_end_transition(final_cell: Vector2i) -> Dictionary:
	return BoardInteractionSystemScript.resolve_turn_end_transition(self, final_cell, BoardInteractionSystemScript.ACTOR_PLAYER)


func has_wall_between(a: Vector2i, b: Vector2i) -> bool:
	return has_shared_wall_between(a, b)


func has_shared_wall_between(a: Vector2i, b: Vector2i) -> bool:
	return BoardInteractionSystemScript.has_shared_wall_between(self, a, b)


func has_player_wall_between(a: Vector2i, b: Vector2i) -> bool:
	return BoardInteractionSystemScript.is_blocked(self, a, b, BoardInteractionSystemScript.ACTOR_PLAYER)


func has_enemy_wall_between(a: Vector2i, b: Vector2i) -> bool:
	return BoardInteractionSystemScript.is_blocked(self, a, b, BoardInteractionSystemScript.ACTOR_ENEMY)


func can_step(a: Vector2i, b: Vector2i) -> bool:
	return can_player_step(a, b)


func can_player_step(a: Vector2i, b: Vector2i) -> bool:
	return BoardInteractionSystemScript.can_step(self, a, b, BoardInteractionSystemScript.ACTOR_PLAYER)


func can_enemy_step(a: Vector2i, b: Vector2i) -> bool:
	return BoardInteractionSystemScript.can_step(self, a, b, BoardInteractionSystemScript.ACTOR_ENEMY)


func get_cardinal_neighbors(cell: Vector2i) -> Array[Vector2i]:
	return get_player_cardinal_neighbors(cell)


func get_player_cardinal_neighbors(cell: Vector2i) -> Array[Vector2i]:
	return BoardInteractionSystemScript.cardinal_neighbors(self, cell, BoardInteractionSystemScript.ACTOR_PLAYER)


func get_enemy_cardinal_neighbors(cell: Vector2i) -> Array[Vector2i]:
	return BoardInteractionSystemScript.cardinal_neighbors(self, cell, BoardInteractionSystemScript.ACTOR_ENEMY)


func get_move_options(cell: Vector2i, include_skip: bool = true) -> Array[String]:
	var options: Array[String] = []
	if include_skip:
		options.append("skip")

	for action in ["right", "left", "up", "down"]:
		var next_cell: Vector2i = apply_action(cell, action)
		if next_cell != cell:
			options.append(action)

	return options


func apply_cardinal_action(cell: Vector2i, action: String) -> Vector2i:
	return BoardInteractionSystemScript.apply_cardinal_action(self, cell, action, BoardInteractionSystemScript.ACTOR_PLAYER)


func apply_action(cell: Vector2i, action: String) -> Vector2i:
	return resolve_player_transition(cell, action).get("resolved_cell", cell)


func build_floor_lookup() -> Dictionary:
	return _floor_lookup.duplicate()


func to_saved_payload(next_display_name: String = "", next_saved_at_unix: int = 0) -> Dictionary:
	return {
		"version": SAVE_VERSION,
		"display_name": next_display_name,
		"saved_at_unix": next_saved_at_unix,
		"width": width,
		"height": height,
		"cell_size": cell_size,
		"size_category": size_category,
		"difficulty_category": difficulty_category,
		"horizontal_walls": horizontal_walls.duplicate(),
		"vertical_walls": vertical_walls.duplicate(),
		"player_horizontal_walls": player_horizontal_walls.duplicate(),
		"player_vertical_walls": player_vertical_walls.duplicate(),
		"enemy_horizontal_walls": enemy_horizontal_walls.duplicate(),
		"enemy_vertical_walls": enemy_vertical_walls.duplicate(),
		"one_way_passages": one_way_passages.duplicate(true),
		"teleport_pairs": teleport_pairs.duplicate(true),
		"enemy_teleport_pairs": enemy_teleport_pairs.duplicate(true),
		"shared_teleport_pairs": shared_teleport_pairs.duplicate(true),
		"trap_cells": trap_cells.duplicate(),
		"player_spawn": player_spawn,
		"enemy_spawns": enemy_spawns.duplicate(true),
		"minotaur_spawn": minotaur_spawn,
		"exit_cell": exit_cell,
		"main_exit_cell": exit_cell,
		"exit_cells": exit_cells.duplicate(),
		"main_exit_cells": get_main_exit_cells(),
		"win_zone_cells": get_win_zone_cells(),
		"escape_zone_cells": escape_zone_cells.duplicate(),
		"zone_spawners": zone_spawners.duplicate(true),
		"escape_zone_spawners": zone_spawners.duplicate(true),
		"solution_actions": solution_actions.duplicate(),
		"solution_total_steps": solution_total_steps,
		"generation_mode": generation_mode,
		"generation_profile_id": generation_profile_id,
	}


static func from_saved_payload(payload: Dictionary) -> MazeData:
	var board := MazeData.new()
	board.width = int(payload.get("width", 0))
	board.height = int(payload.get("height", 0))
	board.cell_size = int(payload.get("cell_size", 16))
	board.size_category = String(payload.get("size_category", "small"))
	board.difficulty_category = String(payload.get("difficulty_category", "easy"))
	board.display_name = String(payload.get("display_name", ""))
	board.saved_at_unix = int(payload.get("saved_at_unix", 0))
	board.player_spawn = board._coerce_vector2i(payload.get("player_spawn", Vector2i.ZERO))
	board.minotaur_spawn = board._coerce_vector2i(payload.get("minotaur_spawn", Vector2i.ZERO))
	board.enemy_spawns = EnemySpawnDataScript.coerce_enemy_spawn_array(payload.get("enemy_spawns", []), board.minotaur_spawn, true)
	board.minotaur_spawn = EnemySpawnDataScript.first_enemy_cell(board.enemy_spawns, board.minotaur_spawn)
	board.exit_cell = board._resolve_main_exit_cell_from_payload(payload, "main_exit_cell", "exit_cell")
	var raw_exit_cells = board._resolve_main_exit_cells_from_payload(payload, "main_exit_cells", "exit_cells", board.exit_cell)
	if raw_exit_cells.is_empty():
		raw_exit_cells = [board.exit_cell]
	for raw_exit_cell in raw_exit_cells:
		board.add_exit_cell(board._coerce_vector2i(raw_exit_cell))
	for raw_escape_zone_cell in payload.get("escape_zone_cells", []):
		board.add_escape_zone_cell(board._coerce_vector2i(raw_escape_zone_cell))
	board.zone_spawners = board._coerce_dictionary_array(payload.get("escape_zone_spawners", payload.get("zone_spawners", [])))
	board.generation_mode = String(payload.get("generation_mode", "RUNTIME_GENERATED"))
	board.generation_profile_id = String(payload.get("generation_profile_id", ""))
	board.solution_total_steps = int(payload.get("solution_total_steps", 0))

	for y in range(board.height):
		for x in range(board.width):
			board.add_floor_cell(Vector2i(x, y))

	for horizontal_wall in payload.get("horizontal_walls", []):
		board.add_horizontal_wall(board._coerce_vector2i(horizontal_wall))

	for vertical_wall in payload.get("vertical_walls", []):
		board.add_vertical_wall(board._coerce_vector2i(vertical_wall))

	for horizontal_wall in payload.get("player_horizontal_walls", []):
		board.add_player_horizontal_wall(board._coerce_vector2i(horizontal_wall))

	for vertical_wall in payload.get("player_vertical_walls", []):
		board.add_player_vertical_wall(board._coerce_vector2i(vertical_wall))

	for horizontal_wall in payload.get("enemy_horizontal_walls", []):
		board.add_enemy_horizontal_wall(board._coerce_vector2i(horizontal_wall))

	for vertical_wall in payload.get("enemy_vertical_walls", []):
		board.add_enemy_vertical_wall(board._coerce_vector2i(vertical_wall))

	for raw_passage in payload.get("one_way_passages", []):
		board.add_one_way_passage(raw_passage)

	for teleport_pair in payload.get("teleport_pairs", []):
		board.add_teleport_pair(teleport_pair)
	for enemy_teleport_pair in payload.get("enemy_teleport_pairs", []):
		board.add_enemy_teleport_pair(enemy_teleport_pair)
	for shared_teleport_pair in payload.get("shared_teleport_pairs", []):
		board.add_shared_teleport_pair(shared_teleport_pair)

	for trap_cell in payload.get("trap_cells", []):
		board.add_trap_cell(board._coerce_vector2i(trap_cell))

	for action in payload.get("solution_actions", []):
		board.solution_actions.append(String(action))

	if board.solution_total_steps <= 0:
		board.solution_total_steps = board.solution_actions.size()

	board.wall_density = float(board.horizontal_walls.size() + board.vertical_walls.size()) / max(float(board._edge_count()), 1.0)
	board.maze_key = board._build_maze_key_from_state()
	return board


static func from_saved_resource(saved_resource: Resource) -> MazeData:
	if saved_resource == null:
		return null
	if saved_resource.has_method("to_payload"):
		return from_saved_payload(saved_resource.to_payload())
	return null


func _add_wall_from_edge(raw_wall, wall_scope: String = "shared") -> void:
	var nodes: Array = raw_wall
	if nodes.size() != 2:
		return

	var a: Vector2i = _coerce_vector2i(nodes[0])
	var b: Vector2i = _coerce_vector2i(nodes[1])
	var delta := b - a
	if abs(delta.x) + abs(delta.y) != 1:
		return

	if delta.x != 0:
		var vertical_edge := Vector2i(max(a.x, b.x), a.y)
		match wall_scope:
			"player":
				add_player_vertical_wall(vertical_edge)
			"enemy":
				add_enemy_vertical_wall(vertical_edge)
			_:
				add_vertical_wall(vertical_edge)
	else:
		var horizontal_edge := Vector2i(a.x, max(a.y, b.y))
		match wall_scope:
			"player":
				add_player_horizontal_wall(horizontal_edge)
			"enemy":
				add_enemy_horizontal_wall(horizontal_edge)
			_:
				add_horizontal_wall(horizontal_edge)


func _build_maze_key_from_state() -> Dictionary:
	var serialized_walls: Array = []
	var serialized_player_only_walls: Array = []
	var serialized_enemy_only_walls: Array = []

	for edge in horizontal_walls:
		serialized_walls.append([
			[edge.x, edge.y - 1],
			[edge.x, edge.y],
		])

	for edge in vertical_walls:
		serialized_walls.append([
			[edge.x - 1, edge.y],
			[edge.x, edge.y],
		])

	for edge in player_horizontal_walls:
		serialized_player_only_walls.append([
			[edge.x, edge.y - 1],
			[edge.x, edge.y],
		])

	for edge in player_vertical_walls:
		serialized_player_only_walls.append([
			[edge.x - 1, edge.y],
			[edge.x, edge.y],
		])

	for edge in enemy_horizontal_walls:
		serialized_enemy_only_walls.append([
			[edge.x, edge.y - 1],
			[edge.x, edge.y],
		])

	for edge in enemy_vertical_walls:
		serialized_enemy_only_walls.append([
			[edge.x - 1, edge.y],
			[edge.x, edge.y],
		])

	return {
		"size_board": [width, height],
		"walls": serialized_walls,
		"player_only_walls": serialized_player_only_walls,
		"enemy_only_walls": serialized_enemy_only_walls,
		"one_way_passages": one_way_passages.duplicate(true),
		"teleport_pairs": teleport_pairs.duplicate(true),
		"enemy_teleport_pairs": enemy_teleport_pairs.duplicate(true),
		"shared_teleport_pairs": shared_teleport_pairs.duplicate(true),
		"trap_cells": trap_cells.duplicate(),
		"player_start": [player_spawn.x, player_spawn.y],
		"enemy_spawns": enemy_spawns.duplicate(true),
		"mino_start": [minotaur_spawn.x, minotaur_spawn.y],
		"goal": [exit_cell.x, exit_cell.y],
		"main_exit_cell": [exit_cell.x, exit_cell.y],
		"goal_cells": exit_cells.duplicate(),
		"main_exit_cells": get_main_exit_cells(),
		"win_zone_cells": get_win_zone_cells(),
		"escape_zone_cells": escape_zone_cells.duplicate(),
		"zone_spawners": zone_spawners.duplicate(true),
		"escape_zone_spawners": zone_spawners.duplicate(true),
		"solution": solution_actions.duplicate(),
		"sol_length": solution_total_steps,
	}


func _edge_count() -> int:
	return width * max(height - 1, 0) + max(width - 1, 0) * height


func _directed_edge_key(a: Vector2i, b: Vector2i) -> String:
	return "%d,%d>%d,%d" % [a.x, a.y, b.x, b.y]


func _coerce_vector2i(raw_value) -> Vector2i:
	if raw_value is Vector2i:
		return raw_value
	if raw_value is Vector2:
		return Vector2i(int(raw_value.x), int(raw_value.y))
	if raw_value is Array and raw_value.size() >= 2:
		return Vector2i(int(raw_value[0]), int(raw_value[1]))
	return Vector2i.ZERO


func _coerce_dictionary_array(raw_value) -> Array[Dictionary]:
	var coerced: Array[Dictionary] = []
	for entry in raw_value:
		if entry is Dictionary:
			coerced.append(entry.duplicate(true))
	return coerced


func _resolve_main_exit_cell_from_payload(payload: Dictionary, preferred_key: String, fallback_key: String) -> Vector2i:
	var preferred_cell := _coerce_vector2i(payload.get(preferred_key, Vector2i.ZERO))
	if preferred_cell != Vector2i.ZERO:
		return preferred_cell

	var fallback_cell := _coerce_vector2i(payload.get(fallback_key, Vector2i.ZERO))
	if fallback_cell != Vector2i.ZERO:
		return fallback_cell

	var preferred_cells = _coerce_vector2i_array(payload.get(preferred_key.replace("_cell", "_cells"), []))
	if not preferred_cells.is_empty():
		return preferred_cells[0]

	var fallback_cells = _coerce_vector2i_array(payload.get(fallback_key.replace("_cell", "_cells"), []))
	if not fallback_cells.is_empty():
		return fallback_cells[0]

	return preferred_cell


func _resolve_main_exit_cells_from_payload(
	payload: Dictionary,
	preferred_key: String,
	fallback_key: String,
	fallback_cell: Vector2i
) -> Array:
	var preferred_cells = _coerce_vector2i_array(payload.get(preferred_key, []))
	if not preferred_cells.is_empty():
		return preferred_cells

	var fallback_cells = _coerce_vector2i_array(payload.get(fallback_key, []))
	if not fallback_cells.is_empty():
		return fallback_cells

	return [fallback_cell]


func _coerce_vector2i_array(raw_value) -> Array[Vector2i]:
	var coerced: Array[Vector2i] = []
	for entry in raw_value:
		coerced.append(_coerce_vector2i(entry))
	return coerced
