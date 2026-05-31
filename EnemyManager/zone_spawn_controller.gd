extends RefCounted
class_name ZoneSpawnController

const INVALID_SPAWN_CELL := Vector2i(-9999, -9999)

var board_state: MazeData
var _spawner_states: Array[Dictionary] = []


func setup(next_board_state: MazeData) -> void:
	board_state = next_board_state
	_spawner_states.clear()
	if board_state == null:
		return

	for spawner_data in board_state.get_escape_zone_spawners():
		var interval: int = int(spawner_data.get("spawn_interval_turns", 2))
		_spawner_states.append({
			"id": String(spawner_data.get("id", "")),
			"turns_until_spawn": int(spawner_data.get("initial_delay_turns", interval)),
		})


func build_state_snapshot() -> Array[Dictionary]:
	return _spawner_states.duplicate(true)


func restore_state_snapshot(raw_states) -> void:
	_spawner_states.clear()
	for entry in raw_states:
		if not entry is Dictionary:
			continue
		_spawner_states.append(entry.duplicate(true))


func warning_cells(player_cell: Vector2i, occupied_cells: Array[Vector2i]) -> Array[Vector2i]:
	var warning_cells: Array[Vector2i] = []
	if board_state == null:
		return warning_cells

	var spawners := board_state.get_escape_zone_spawners()
	for spawner_index in range(min(_spawner_states.size(), spawners.size())):
		var spawner_state: Dictionary = _spawner_states[spawner_index]
		if int(spawner_state.get("turns_until_spawn", 0)) != 1:
			continue
		var spawn_cell := _choose_spawner_cell(spawners[spawner_index], player_cell, occupied_cells)
		if spawn_cell == INVALID_SPAWN_CELL:
			continue
		warning_cells.append(spawn_cell)
	return warning_cells


func advance(player_cell: Vector2i, occupied_cells: Array[Vector2i]) -> Array[Dictionary]:
	var spawned_configs: Array[Dictionary] = []
	if board_state == null:
		return spawned_configs

	var spawners := board_state.get_escape_zone_spawners()
	for spawner_index in range(min(_spawner_states.size(), spawners.size())):
		var spawner_state: Dictionary = _spawner_states[spawner_index]
		var turns_until_spawn: int = int(spawner_state.get("turns_until_spawn", 0)) - 1
		if turns_until_spawn > 0:
			spawner_state["turns_until_spawn"] = turns_until_spawn
			_spawner_states[spawner_index] = spawner_state
			continue

		var spawner_data: Dictionary = spawners[spawner_index]
		var spawn_cell := _choose_spawner_cell(spawner_data, player_cell, occupied_cells)
		if spawn_cell == INVALID_SPAWN_CELL:
			spawner_state["turns_until_spawn"] = 1
			_spawner_states[spawner_index] = spawner_state
			continue

		spawned_configs.append(_build_spawn_configuration(spawner_data, spawn_cell))
		occupied_cells.append(spawn_cell)
		spawner_state["turns_until_spawn"] = int(spawner_data.get("spawn_interval_turns", 2))
		_spawner_states[spawner_index] = spawner_state

	return spawned_configs


func _build_spawn_configuration(spawner_data: Dictionary, spawn_cell: Vector2i) -> Dictionary:
	return {
		"type": String(spawner_data.get("enemy_type", "linked_escape_hunter")),
		"role": String(spawner_data.get("role", "linked_escape_hunter")),
		"movement_type": String(spawner_data.get("movement_type", "astar")),
		"cell": spawn_cell,
		"move_priority": String(spawner_data.get("move_priority", "horizontal")),
		"step_count": int(spawner_data.get("step_count", 2)),
		"facing_index": int(spawner_data.get("facing_index", 2)),
		"traits": spawner_data.get("traits", ["escape_linked"]),
		"wake_goal_distance": -1,
		"lifetime_turns": int(spawner_data.get("lifetime_turns", 3)),
		"patrol_route": spawner_data.get("patrol_route", []),
		"behavior_seed": int(spawner_data.get("behavior_seed", 0)),
	}


func _choose_spawner_cell(spawner_data: Dictionary, player_cell: Vector2i, occupied_cells: Array[Vector2i]) -> Vector2i:
	var candidate_cells: Array = spawner_data.get("spawn_candidates", [])
	var occupied_lookup: Dictionary = {}
	for occupied_cell in occupied_cells:
		occupied_lookup[occupied_cell] = true

	var available: Array[Vector2i] = []
	for raw_candidate in candidate_cells:
		var candidate: Vector2i = raw_candidate
		if occupied_lookup.has(candidate):
			continue
		available.append(candidate)
	if available.is_empty():
		return INVALID_SPAWN_CELL

	available.sort_custom(func(a: Vector2i, b: Vector2i) -> bool:
		var a_distance := absi(a.x - player_cell.x) + absi(a.y - player_cell.y)
		var b_distance := absi(b.x - player_cell.x) + absi(b.y - player_cell.y)
		if a_distance == b_distance:
			if a.y == b.y:
				return a.x < b.x
			return a.y < b.y
		return a_distance > b_distance
	)
	return available[0]
