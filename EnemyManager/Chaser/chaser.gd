extends "res://EnemyManager/enemy_base.gd"

const AStarChaserLogicScript = preload("res://EnemyManager/AStarChaser/astar_chaser_logic.gd")
const ChaserLogicScript = preload("res://EnemyManager/chaser_logic.gd")

var role: String = ""
var movement_type: String = "greedy"
var move_priority: String = "horizontal"
var step_count: int = 2
var wake_goal_distance: int = -1
var lifetime_turns: int = -1
var turns_remaining: int = -1
var activated := true


func _ready() -> void:
	enemy_type = "chaser"
	super._ready()


func configure(spawn_data: Dictionary, next_board_state) -> void:
	role = String(spawn_data.get("role", role))
	movement_type = String(spawn_data.get("movement_type", movement_type))
	move_priority = String(spawn_data.get("move_priority", "horizontal"))
	step_count = int(spawn_data.get("step_count", 2))
	wake_goal_distance = int(spawn_data.get("wake_goal_distance", -1))
	lifetime_turns = int(spawn_data.get("lifetime_turns", -1))
	turns_remaining = lifetime_turns
	activated = wake_goal_distance < 0
	super.configure(spawn_data, next_board_state)


func get_step_count() -> int:
	return step_count


func choose_target_cell(player_cell: Vector2i, occupied_lookup: Dictionary) -> Vector2i:
	if movement_type == "astar":
		return AStarChaserLogicScript.choose_astar_step(
			current_cell,
			player_cell,
			occupied_lookup,
			board_state
		)
	return _choose_greedy_step(player_cell, occupied_lookup)


func begin_turn(player_cell: Vector2i) -> bool:
	if is_dead:
		return false
	if not activated and wake_goal_distance >= 0:
		var distance_to_exit: int = int(board_state.goal_distance_from_player_cell(player_cell))
		if distance_to_exit >= 0 and distance_to_exit <= wake_goal_distance:
			activated = true
	return activated


func end_turn() -> void:
	if not activated or lifetime_turns < 0 or is_dead:
		return
	turns_remaining -= 1
	if turns_remaining <= 0:
		mark_dead()


func take_turn(player_cell: Vector2i, occupied_cells: Array[Vector2i]) -> Dictionary:
	var occupied_lookup: Dictionary = {}
	for cell in occupied_cells:
		if cell != current_cell:
			occupied_lookup[cell] = true

	var previous_cell: Vector2i = current_cell

	for _step in step_count:
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
		"spawn_order": spawn_order,
		"traits": traits.duplicate(),
		"previous_cell": previous_cell,
		"new_cell": current_cell,
		"contact_player": current_cell == player_cell,
		"died": false,
		"killed_spawn_order": -1,
	}

	return result


func _choose_greedy_step(player_cell: Vector2i, occupied_lookup: Dictionary) -> Vector2i:
	return ChaserLogicScript.choose_greedy_step(
		current_cell,
		player_cell,
		occupied_lookup,
		board_state,
		move_priority
	)


func build_spawn_snapshot() -> Dictionary:
	var snapshot := super.build_spawn_snapshot()
	snapshot["role"] = role
	snapshot["movement_type"] = movement_type
	snapshot["move_priority"] = move_priority
	snapshot["step_count"] = step_count
	snapshot["wake_goal_distance"] = wake_goal_distance
	snapshot["lifetime_turns"] = lifetime_turns
	return snapshot


func _build_shared_state_snapshot() -> Dictionary:
	return {
		"activated": activated,
		"turns_remaining": turns_remaining,
	}


func _restore_shared_state_snapshot(state: Dictionary) -> void:
	activated = bool(state.get("activated", activated))
	turns_remaining = int(state.get("turns_remaining", turns_remaining))
