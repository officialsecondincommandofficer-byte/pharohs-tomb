extends "res://EnemyManager/enemy_base.gd"

const PATROL_MODE_LOOP := "loop"
const PATROL_MODE_PING_PONG := "ping_pong"

var patrol_mode := PATROL_MODE_PING_PONG


func _ready() -> void:
	enemy_type = "patroller"
	super._ready()


func configure(spawn_data: Dictionary, next_board_state) -> void:
	patrol_mode = String(spawn_data.get("patrol_mode", PATROL_MODE_PING_PONG))
	super.configure(spawn_data, next_board_state)


func choose_target_cell(_player_cell: Vector2i, occupied_lookup: Dictionary) -> Vector2i:
	if patrol_route.size() <= 1:
		return current_cell

	var next_index := patrol_index + patrol_direction
	var next_direction := patrol_direction
	if patrol_mode == PATROL_MODE_LOOP:
		next_index = (patrol_index + 1) % patrol_route.size()
	else:
		if next_index < 0 or next_index >= patrol_route.size():
			patrol_direction *= -1
			next_direction = patrol_direction
			next_index = patrol_index + patrol_direction

	var target_cell: Vector2i = patrol_route[next_index]
	if not _can_enter(target_cell, occupied_lookup):
		if patrol_mode == PATROL_MODE_LOOP:
			return current_cell
		patrol_direction *= -1
		next_direction = patrol_direction
		next_index = patrol_index + patrol_direction
		if next_index < 0 or next_index >= patrol_route.size():
			return current_cell
		target_cell = patrol_route[next_index]
		if not _can_enter(target_cell, occupied_lookup):
			return current_cell

	patrol_index = next_index
	patrol_direction = next_direction
	return target_cell


func build_spawn_snapshot() -> Dictionary:
	var snapshot := super.build_spawn_snapshot()
	snapshot["patrol_mode"] = patrol_mode
	return snapshot


func _build_behavior_state_snapshot() -> Dictionary:
	return {
		"patrol_index": patrol_index,
		"patrol_direction": patrol_direction,
	}


func _restore_behavior_state_snapshot(state: Dictionary) -> void:
	patrol_index = clampi(int(state.get("patrol_index", patrol_index)), 0, max(patrol_route.size() - 1, 0))
	patrol_direction = 1 if int(state.get("patrol_direction", patrol_direction)) >= 0 else -1
