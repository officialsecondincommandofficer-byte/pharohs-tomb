extends Node2D

signal enemy_phase_finished(enemy_results)

const ZoneSpawnControllerScript := preload("res://EnemyManager/zone_spawn_controller.gd")
const CHASER_SCENE := preload("res://EnemyManager/Chaser/Chaser.tscn")
const MINOTAUR_SCENE := preload("res://EnemyManager/Minotaur/Minotaur.tscn")
const PATROLLER_SCENE := preload("res://EnemyManager/Patroller/Patroller.tscn")
const SAMURAI_SCENE := preload("res://EnemyManager/Samurai/Samurai.tscn")
const STATIONARY_BLOCKER_SCENE := preload("res://EnemyManager/StationaryBlocker/StationaryBlocker.tscn")
const WANDERER_SCENE := preload("res://EnemyManager/Wanderer/Wanderer.tscn")
const TRAIT_KILLER := "killer"
const CONTACT_BLOCKED := "blocked"
const CONTACT_TARGET_DIES := "target_dies"
const CONTACT_MOVER_DIES := "mover_dies"

var board_state: MazeData
var _dynamic_spawn_order: int = 0
var _zone_spawn_controller = ZoneSpawnControllerScript.new()


func setup_floor(next_board_state: MazeData) -> void:
	board_state = next_board_state
	for child in get_children():
		child.free()

	for spawn_index in range(board_state.enemy_spawns.size()):
		_spawn_enemy_from_data(board_state.enemy_spawns[spawn_index], spawn_index)

	_zone_spawn_controller.setup(board_state)
	_dynamic_spawn_order = board_state.enemy_spawns.size()
	_refresh_enemy_intents()


func begin_enemy_phase(player_cell: Vector2i) -> Array:
	_advance_zone_spawners(player_cell)
	if get_child_count() == 0:
		enemy_phase_finished.emit([])
		return []

	var results: Array = []
	for enemy_index in range(get_child_count()):
		var enemy = get_child(enemy_index)
		if enemy.is_dead:
			continue

		var result: Dictionary = await _take_enemy_turn(enemy_index, player_cell)
		results.append(result)

	_refresh_enemy_intents()
	enemy_phase_finished.emit(results)
	return results


func get_current_cell() -> Vector2i:
	for child in get_children():
		if _enemy_occupies_cell(child):
			return child.current_cell
	return Vector2i.ZERO


func get_current_cells() -> Array[Vector2i]:
	var cells: Array[Vector2i] = []
	for child in get_children():
		if _enemy_occupies_cell(child):
			cells.append(child.current_cell)
	return cells


func set_cell_immediate(cell: Vector2i) -> void:
	if get_child_count() == 0:
		return
	var enemy = get_child(0)
	enemy.configure(_build_spawn_configuration(0), board_state)
	enemy.restore_to_cell(cell, true)
	_refresh_enemy_intents()


func set_cells_immediate(cells: Array) -> void:
	for index in range(get_child_count()):
		if index >= cells.size():
			get_child(index).restore_to_cell(get_child(index).current_cell, false)
			continue
		var enemy = get_child(index)
		if index < board_state.enemy_spawns.size():
			enemy.configure(_build_spawn_configuration(index), board_state)
		var cell: Vector2i = cells[index]
		enemy.restore_to_cell(cell, true)
	_refresh_enemy_intents()


func get_enemy_states() -> Dictionary:
	var enemy_states: Array[Dictionary] = []
	for child in get_children():
		enemy_states.append(child.build_state_snapshot())
	return {
		"enemies": enemy_states,
		"spawner_states": _zone_spawn_controller.build_state_snapshot(),
		"dynamic_spawn_order": _dynamic_spawn_order,
	}


func restore_enemy_states(enemy_states) -> void:
	var state_payload: Dictionary = {}
	var serialized_enemies: Array = []
	if enemy_states is Dictionary:
		state_payload = enemy_states
		serialized_enemies = state_payload.get("enemies", [])
		_zone_spawn_controller.restore_state_snapshot(state_payload.get("spawner_states", []))
		_dynamic_spawn_order = int(state_payload.get("dynamic_spawn_order", board_state.enemy_spawns.size()))
	else:
		serialized_enemies = enemy_states
		_zone_spawn_controller.setup(board_state)
		_dynamic_spawn_order = board_state.enemy_spawns.size()

	for child in get_children():
		child.free()
	for enemy_state in serialized_enemies:
		if not enemy_state is Dictionary:
			continue
		var config: Dictionary = enemy_state.get("config", {})
		_spawn_enemy_from_data(config, int(config.get("spawn_order", 0)))
		get_child(get_child_count() - 1).restore_from_state(enemy_state)
	_refresh_enemy_intents()


func any_enemy_at_cell(cell: Vector2i) -> bool:
	for child in get_children():
		if _enemy_occupies_cell(child) and child.current_cell == cell:
			return true
	return false


func update_visibility(_visible_cells: Array[Vector2i]) -> void:
	for child in get_children():
		child.visible = _enemy_occupies_cell(child)
	_refresh_enemy_intents()


func get_spawn_warning_cells(player_cell: Vector2i) -> Array[Vector2i]:
	return _zone_spawn_controller.warning_cells(player_cell, get_current_cells())


func _take_enemy_turn(enemy_index: int, player_cell: Vector2i) -> Dictionary:
	var enemy = get_child(enemy_index)
	var previous_cell: Vector2i = enemy.current_cell
	var result := {
		"enemy_type": enemy.enemy_type,
		"spawn_order": enemy.spawn_order,
		"traits": enemy.traits.duplicate(),
		"previous_cell": previous_cell,
		"new_cell": enemy.current_cell,
		"contact_player": false,
		"died": false,
		"killed_spawn_order": -1,
	}

	if enemy.has_method("begin_turn") and not enemy.begin_turn(player_cell):
		result["died"] = enemy.is_dead
		return result

	for _step in range(enemy.get_step_count()):
		if enemy.is_dead:
			break

		var blocked_lookup: Dictionary = _build_blocked_lookup_for_mover(enemy_index)
		var next_cell: Vector2i = enemy.choose_target_cell(player_cell, blocked_lookup)
		if next_cell == enemy.current_cell:
			continue
		var target_index := _active_enemy_index_at_cell(next_cell, enemy_index)
		if target_index != -1:
			var contact_result := _resolve_enemy_contact(enemy_index, target_index)
			if contact_result == CONTACT_BLOCKED:
				continue

			await enemy.move_to_cell(next_cell)
			result["new_cell"] = enemy.current_cell

			if contact_result == CONTACT_TARGET_DIES:
				var target = get_child(target_index)
				result["killed_spawn_order"] = target.spawn_order
				target.mark_dead()
			elif contact_result == CONTACT_MOVER_DIES:
				enemy.mark_dead()
				result["died"] = true
			break

		await enemy.move_to_cell(next_cell)
		result["new_cell"] = enemy.current_cell
		if enemy.current_cell == player_cell:
			result["contact_player"] = true
			break

	if not enemy.is_dead:
		var turn_end_transition: Dictionary = board_state.resolve_enemy_turn_end_transition(enemy.current_cell)
		var resolved_cell: Vector2i = turn_end_transition.get("resolved_cell", enemy.current_cell)
		if resolved_cell != enemy.current_cell:
			var target_index := _active_enemy_index_at_cell(resolved_cell, enemy_index)
			if target_index != -1:
				var contact_result := _resolve_enemy_contact(enemy_index, target_index)
				if contact_result == CONTACT_TARGET_DIES:
					enemy.restore_to_cell(resolved_cell, true)
					result["new_cell"] = enemy.current_cell
					var target = get_child(target_index)
					result["killed_spawn_order"] = target.spawn_order
					target.mark_dead()
				elif contact_result == CONTACT_MOVER_DIES:
					enemy.mark_dead()
					result["died"] = true
			else:
				enemy.restore_to_cell(resolved_cell, true)
				result["new_cell"] = enemy.current_cell
				if enemy.current_cell == player_cell:
					result["contact_player"] = true

	if enemy.has_method("end_turn"):
		enemy.end_turn()
	if enemy.is_dead:
		result["died"] = true
	result["new_cell"] = enemy.current_cell
	return result


func _build_blocked_lookup_for_mover(mover_index: int) -> Dictionary:
	var blocked_lookup: Dictionary = {}
	for target_index in range(get_child_count()):
		if target_index == mover_index:
			continue
		var target = get_child(target_index)
		if not _enemy_occupies_cell(target):
			continue
		if _resolve_enemy_contact(mover_index, target_index) == CONTACT_BLOCKED:
			blocked_lookup[target.current_cell] = true
	return blocked_lookup


func _active_enemy_index_at_cell(cell: Vector2i, excluded_index: int) -> int:
	for index in range(get_child_count()):
		if index == excluded_index:
			continue
		var enemy = get_child(index)
		if not _enemy_occupies_cell(enemy):
			continue
		if enemy.current_cell == cell:
			return index
	return -1


func _resolve_enemy_contact(mover_index: int, target_index: int) -> String:
	var mover = get_child(mover_index)
	var target = get_child(target_index)
	var mover_is_killer: bool = mover.has_trait(TRAIT_KILLER)
	var target_is_killer: bool = target.has_trait(TRAIT_KILLER)

	if target_is_killer:
		if mover_is_killer and mover.spawn_order < target.spawn_order:
			return CONTACT_TARGET_DIES
		return CONTACT_MOVER_DIES

	if mover_is_killer:
		return CONTACT_TARGET_DIES

	return CONTACT_BLOCKED


func _enemy_occupies_cell(enemy) -> bool:
	if enemy.is_dead:
		return false
	if enemy.has_method("occupies_cell"):
		return enemy.occupies_cell()
	return true


func _tint_for_spawn(spawn_data: Dictionary) -> Color:
	if spawn_data.has("tint"):
		return spawn_data["tint"]
	if String(spawn_data.get("role", "")) == "linked_escape_hunter" or Array(spawn_data.get("traits", [])).has("escape_linked"):
		return Color(0.88, 0.78, 0.32, 1.0)
	if String(spawn_data.get("role", "")) == "dasher":
		return Color(0.7, 0.7, 0.78, 1.0)
	if String(spawn_data.get("role", "")) == "stationary_blocker":
		return Color(0.95, 0.95, 0.55, 1.0)
	if String(spawn_data.get("role", "")) == "patroller":
		return Color(0.65, 0.85, 1.0, 1.0)
	if String(spawn_data.get("role", "")) == "wanderer":
		return Color(1.0, 0.8, 0.55, 1.0)
	if String(spawn_data.get("type", "greedy_chaser")) == "samurai":
		return Color(0.7, 0.7, 0.78, 1.0)
	if String(spawn_data.get("move_priority", "horizontal")) == "vertical":
		return Color(0.2, 0.52, 0.95, 1.0)
	return Color(0.92, 0.24, 0.18, 1.0)


func _scene_for_spawn(spawn_data: Dictionary) -> PackedScene:
	var role := String(spawn_data.get("role", ""))
	match String(spawn_data.get("type", "greedy_chaser")):
		"chaser", "greedy_chaser", "linked_escape_hunter", "astar_chaser", "x_chaser", "y_chaser":
			return CHASER_SCENE
		"patroller":
			return PATROLLER_SCENE
		"stationary_blocker":
			return STATIONARY_BLOCKER_SCENE
		"wanderer":
			return WANDERER_SCENE
		"minotaur":
			return MINOTAUR_SCENE
		"samurai", "dasher":
			return SAMURAI_SCENE
		_:
			if role == "dasher":
				return SAMURAI_SCENE
			return CHASER_SCENE


func _build_spawn_configuration(spawn_index: int) -> Dictionary:
	var spawn_data: Dictionary = board_state.enemy_spawns[spawn_index].duplicate(true)
	spawn_data["spawn_order"] = spawn_index
	spawn_data["tint"] = _tint_for_spawn(spawn_data)
	return spawn_data


func _spawn_enemy_from_data(spawn_data: Dictionary, spawn_order: int) -> void:
	var enemy_scene: PackedScene = _scene_for_spawn(spawn_data)
	var enemy = enemy_scene.instantiate()
	add_child(enemy)
	var configured_spawn := spawn_data.duplicate(true)
	configured_spawn["spawn_order"] = spawn_order
	configured_spawn["tint"] = _tint_for_spawn(configured_spawn)
	enemy.configure(configured_spawn, board_state)


func _refresh_enemy_intents() -> void:
	for enemy_index in range(get_child_count()):
		var enemy = get_child(enemy_index)
		if not _enemy_occupies_cell(enemy):
			continue
		if enemy.has_method("refresh_intent_preview"):
			enemy.refresh_intent_preview(_build_blocked_lookup_for_mover(enemy_index))


func _advance_zone_spawners(player_cell: Vector2i) -> void:
	var occupied_cells := get_current_cells()
	for spawn_data in _zone_spawn_controller.advance(player_cell, occupied_cells):
		_spawn_enemy_from_data(spawn_data, _dynamic_spawn_order)
		_dynamic_spawn_order += 1
