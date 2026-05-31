extends CharacterBody2D

@export var enemy_type: String = "enemy"
@export var tint: Color = Color.WHITE
@export var move_duration: float = 0.12

@onready var anim: AnimatedSprite2D = $AnimatedSprite2D

var board_state
var current_cell: Vector2i = Vector2i.ZERO
var spawn_order: int = 0
var traits: Array[String] = []
var is_dead := false
var patrol_route: Array[Vector2i] = []
var patrol_index := 0
var patrol_direction := 1
var behavior_seed: int = 0


func _ready() -> void:
	anim.modulate = tint


func configure(spawn_data: Dictionary, next_board_state) -> void:
	board_state = next_board_state
	enemy_type = String(spawn_data.get("type", enemy_type))
	spawn_order = int(spawn_data.get("spawn_order", spawn_order))
	traits = _coerce_string_array(spawn_data.get("traits", []))
	var next_tint: Color = spawn_data.get("tint", tint)
	tint = next_tint
	current_cell = spawn_data.get("cell", Vector2i.ZERO)
	is_dead = false
	visible = true
	behavior_seed = int(spawn_data.get("behavior_seed", 0))
	patrol_route.clear()
	var raw_patrol_route: Array = spawn_data.get("patrol_route", [current_cell])
	for patrol_cell in raw_patrol_route:
		patrol_route.append(_coerce_vector2i(patrol_cell))
	if String(spawn_data.get("patrol_mode", "ping_pong")) == "loop" and patrol_route.size() > 1 and patrol_route[0] == patrol_route[patrol_route.size() - 1]:
		patrol_route.remove_at(patrol_route.size() - 1)
	if patrol_route.is_empty():
		patrol_route.append(current_cell)
	patrol_index = 0
	patrol_direction = 1
	position = board_state.to_world(current_cell)
	anim.modulate = tint


func take_turn(player_cell: Vector2i, occupied_cells: Array[Vector2i]) -> Dictionary:
	var occupied_lookup: Dictionary = {}
	for cell in occupied_cells:
		if cell != current_cell:
			occupied_lookup[cell] = true

	var next_cell: Vector2i = choose_target_cell(player_cell, occupied_lookup)
	var result: Dictionary = {
		"enemy_type": enemy_type,
		"spawn_order": spawn_order,
		"traits": traits.duplicate(),
		"previous_cell": current_cell,
		"new_cell": current_cell,
		"contact_player": false,
		"died": false,
		"killed_spawn_order": -1,
	}

	if next_cell == current_cell:
		return result

	current_cell = next_cell
	result["new_cell"] = current_cell
	result["contact_player"] = current_cell == player_cell
	_update_facing(current_cell - result["previous_cell"])
	await _animate_to_world_position(board_state.to_world(current_cell))
	return result


func get_step_count() -> int:
	return 1


func move_to_cell(next_cell: Vector2i) -> void:
	if next_cell == current_cell:
		return
	var step_direction: Vector2i = next_cell - current_cell
	current_cell = next_cell
	_update_facing(step_direction)
	await _animate_to_world_position(board_state.to_world(current_cell))


func mark_dead() -> void:
	is_dead = true
	visible = false


func restore_to_cell(cell: Vector2i, alive: bool) -> void:
	current_cell = cell
	position = board_state.to_world(current_cell)
	is_dead = not alive
	visible = alive


func has_trait(trait_name: String) -> bool:
	return traits.has(trait_name)


func build_state_snapshot() -> Dictionary:
	return {
		"config": build_spawn_snapshot(),
		"cell": current_cell,
		"alive": not is_dead,
		"shared_state": _build_shared_state_snapshot(),
		"behavior_state": _build_behavior_state_snapshot(),
	}


func restore_from_state(enemy_state: Dictionary) -> void:
	var cell: Vector2i = enemy_state.get("cell", current_cell)
	var alive := bool(enemy_state.get("alive", true))
	restore_to_cell(cell, alive)
	var legacy_state: Dictionary = enemy_state.get("state", {})
	_restore_shared_state_snapshot(enemy_state.get("shared_state", legacy_state))
	_restore_behavior_state_snapshot(enemy_state.get("behavior_state", legacy_state))


func choose_target_cell(_player_cell: Vector2i, _occupied_lookup: Dictionary) -> Vector2i:
	return current_cell


func build_spawn_snapshot() -> Dictionary:
	return {
		"type": enemy_type,
		"cell": current_cell,
		"spawn_order": spawn_order,
		"traits": traits.duplicate(),
		"patrol_route": patrol_route.duplicate(),
		"patrol_mode": "ping_pong",
		"behavior_seed": behavior_seed,
	}


func occupies_cell() -> bool:
	return not is_dead


func _build_shared_state_snapshot() -> Dictionary:
	return {}


func _restore_shared_state_snapshot(_state: Dictionary) -> void:
	return


func _build_behavior_state_snapshot() -> Dictionary:
	return {}


func _restore_behavior_state_snapshot(_state: Dictionary) -> void:
	return


func _can_enter(cell: Vector2i, occupied_lookup: Dictionary) -> bool:
	if not board_state.can_enemy_step(current_cell, cell):
		return false
	return not occupied_lookup.has(cell)


func _find_path(start: Vector2i, goal: Vector2i, occupied_lookup: Dictionary) -> Array[Vector2i]:
	var queue: Array[Vector2i] = [start]
	var came_from: Dictionary = {start: start}

	while not queue.is_empty():
		var current: Vector2i = queue.pop_front()
		if current == goal:
			break

		for neighbor in board_state.get_enemy_cardinal_neighbors(current):
			if occupied_lookup.has(neighbor) and neighbor != goal:
				continue
			if came_from.has(neighbor):
				continue
			came_from[neighbor] = current
			queue.append(neighbor)

	if not came_from.has(goal):
		return [start]

	var path: Array[Vector2i] = [goal]
	var cursor := goal
	while cursor != start:
		cursor = came_from[cursor]
		path.push_front(cursor)
	return path


func _update_facing(direction: Vector2i) -> void:
	if direction.x > 0:
		anim.play("walk_right")
	elif direction.x < 0:
		anim.play("walk_left")
	elif direction.y > 0:
		anim.play("walk_downward")
	elif direction.y < 0:
		anim.play("walk_upward")


func _animate_to_world_position(target_position: Vector2) -> void:
	var tween: Tween = create_tween()
	tween.tween_property(self, "position", target_position, move_duration).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	await tween.finished


func _coerce_string_array(raw_value) -> Array[String]:
	var coerced: Array[String] = []
	for entry in raw_value:
		coerced.append(String(entry))
	return coerced


func _coerce_vector2i(raw_value) -> Vector2i:
	if raw_value is Vector2i:
		return raw_value
	if raw_value is Vector2:
		return Vector2i(int(raw_value.x), int(raw_value.y))
	if raw_value is Array and raw_value.size() >= 2:
		return Vector2i(int(raw_value[0]), int(raw_value[1]))
	return Vector2i.ZERO
