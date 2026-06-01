extends RefCounted
class_name EnemyTurnSystem

const EnemyContactSystemScript := preload("res://EnemyManager/enemy_contact_system.gd")
const EnemyLifecycleSystemScript := preload("res://EnemyManager/enemy_lifecycle_system.gd")
const EnemyBehaviorSystemsScript := preload("res://EnemyManager/enemy_behavior_systems.gd")


static func take_enemy_turn(manager, enemy_index: int, player_cell: Vector2i) -> Dictionary:
	var record = manager._runtime_registry.record_at(enemy_index)
	var enemy = record.enemy
	var previous_cell: Vector2i = record.current_cell
	var result := {
		"enemy_type": record.enemy_type,
		"spawn_order": record.spawn_order,
		"traits": record.traits.duplicate(),
		"previous_cell": previous_cell,
		"new_cell": record.current_cell,
		"contact_player": false,
		"died": false,
		"killed_spawn_order": -1,
	}

	if not _begin_turn(record, player_cell, manager.board_state):
		record.apply_to_enemy()
		result["died"] = record.is_dead
		return result

	for _step in range(_step_count(record, enemy)):
		if record.is_dead:
			break

		var blocked_lookup: Dictionary = EnemyContactSystemScript.build_blocked_lookup(manager._runtime_registry, enemy_index)
		var next_cell: Vector2i = _choose_target_cell(record, enemy, player_cell, blocked_lookup, manager.board_state)
		record.apply_to_enemy()
		if next_cell == record.current_cell:
			continue
		var target_index := EnemyContactSystemScript.active_enemy_index_at_cell(manager._runtime_registry, next_cell, enemy_index)
		if target_index != -1:
			var target_record = manager._runtime_registry.record_at(target_index)
			var contact_result := EnemyContactSystemScript.resolve_contact(record, target_record)
			if contact_result == EnemyContactSystemScript.CONTACT_BLOCKED:
				continue

			_update_post_move_state(record, record.current_cell, next_cell)
			record.move_to_cell(next_cell)
			await enemy.present_move_to_cell(next_cell)
			result["new_cell"] = record.current_cell

			if contact_result == EnemyContactSystemScript.CONTACT_TARGET_DIES:
				result["killed_spawn_order"] = target_record.spawn_order
				target_record.mark_dead()
			elif contact_result == EnemyContactSystemScript.CONTACT_MOVER_DIES:
				record.mark_dead()
				result["died"] = true
			break

		_update_post_move_state(record, record.current_cell, next_cell)
		record.move_to_cell(next_cell)
		await enemy.present_move_to_cell(next_cell)
		result["new_cell"] = record.current_cell
		if record.current_cell == player_cell:
			result["contact_player"] = true
			break

	if not record.is_dead:
		var turn_end_transition: Dictionary = manager.board_state.resolve_enemy_turn_end_transition(record.current_cell)
		var resolved_cell: Vector2i = turn_end_transition.get("resolved_cell", record.current_cell)
		if resolved_cell != record.current_cell:
			var target_index := EnemyContactSystemScript.active_enemy_index_at_cell(manager._runtime_registry, resolved_cell, enemy_index)
			if target_index != -1:
				var target_record = manager._runtime_registry.record_at(target_index)
				var contact_result := EnemyContactSystemScript.resolve_contact(record, target_record)
				if contact_result == EnemyContactSystemScript.CONTACT_TARGET_DIES:
					record.restore_to_cell(resolved_cell, true)
					result["new_cell"] = record.current_cell
					result["killed_spawn_order"] = target_record.spawn_order
					target_record.mark_dead()
				elif contact_result == EnemyContactSystemScript.CONTACT_MOVER_DIES:
					record.mark_dead()
					result["died"] = true
			else:
				record.restore_to_cell(resolved_cell, true)
				result["new_cell"] = record.current_cell
				if record.current_cell == player_cell:
					result["contact_player"] = true

	_end_turn(record, enemy, manager.board_state)
	record.apply_to_enemy()
	if record.is_dead:
		result["died"] = true
	result["new_cell"] = record.current_cell
	return result


static func _step_count(record, _enemy) -> int:
	var step_count: int = record.config_int("step_count", 1)
	if step_count > 0:
		return step_count
	return 1


static func _scene_family(record) -> String:
	return record.config_string("scene_family", record.component_string("identity", "scene_family", "chaser"))


static func _begin_turn(record, player_cell: Vector2i, board_state) -> bool:
	if record.is_dead:
		return false
	match _scene_family(record):
		"chaser":
			var activated := bool(record.shared_state.get("activated", record.config_int("wake_goal_distance", -1) < 0))
			activated = managerless_activation(activated, record.config_int("wake_goal_distance", -1), player_cell, board_state)
			record.shared_state["activated"] = activated
			return activated
		_:
			return true


static func _end_turn(record, _enemy, board_state) -> void:
	match _scene_family(record):
		"chaser":
			var activated := bool(record.shared_state.get("activated", record.config_int("wake_goal_distance", -1) < 0))
			var turns_remaining := int(record.shared_state.get("turns_remaining", record.config_int("lifetime_turns", -1)))
			var lifetime_result: Dictionary = EnemyLifecycleSystemScript.advance_lifetime(
				activated,
				record.config_int("lifetime_turns", -1),
				turns_remaining,
				record.is_dead
			)
			record.shared_state["turns_remaining"] = int(lifetime_result.get("turns_remaining", turns_remaining))
			if bool(lifetime_result.get("expired", false)):
				record.mark_dead()


static func managerless_activation(activated: bool, wake_goal_distance: int, player_cell: Vector2i, board_state) -> bool:
	return EnemyLifecycleSystemScript.resolve_activation(
		activated,
		wake_goal_distance,
		player_cell,
		board_state
	)


static func _choose_target_cell(record, enemy, player_cell: Vector2i, blocked_lookup: Dictionary, board_state) -> Vector2i:
	match _scene_family(record):
		"chaser":
			return EnemyBehaviorSystemsScript.choose_chaser_target(
				record.current_cell,
				player_cell,
				blocked_lookup,
				board_state,
				record.config_string("movement_type", "greedy"),
				record.config_string("move_priority", "horizontal")
			)
		"minotaur":
			return EnemyBehaviorSystemsScript.choose_minotaur_target(
				record.current_cell,
				player_cell,
				board_state,
				record.config_string("move_priority", "horizontal")
			)
		"patroller":
			var plan: Dictionary = EnemyBehaviorSystemsScript.choose_patroller_target(
				record.current_cell,
				_coerce_vector2i_array(record.config.get("patrol_route", [])),
				int(record.behavior_state.get("patrol_index", 0)),
				1 if int(record.behavior_state.get("patrol_direction", 1)) >= 0 else -1,
				record.config_string("patrol_mode", "ping_pong"),
				blocked_lookup,
				func(target_cell: Vector2i, occupied: Dictionary) -> bool:
					return _can_record_enter(record, target_cell, occupied, board_state)
			)
			record.behavior_state["patrol_index"] = int(plan.get("patrol_index", 0))
			record.behavior_state["patrol_direction"] = int(plan.get("patrol_direction", 1))
			return plan.get("cell", record.current_cell)
		"samurai":
			var samurai_plan: Dictionary = EnemyBehaviorSystemsScript.choose_samurai_turn_state(
				record.current_cell,
				player_cell,
				blocked_lookup,
				board_state,
				int(record.behavior_state.get("facing_index", record.config_int("facing_index", 2))),
				int(record.behavior_state.get("attack_phase", -1)),
				int(record.behavior_state.get("turns_until_dash", 0))
			)
			record.behavior_state["facing_index"] = int(samurai_plan.get("facing_index", 2))
			record.behavior_state["display_facing_index"] = int(samurai_plan.get("display_facing_index", record.behavior_state.get("facing_index", 2)))
			record.behavior_state["attack_phase"] = int(samurai_plan.get("attack_phase", -1))
			record.behavior_state["turns_until_dash"] = int(samurai_plan.get("turns_until_dash", 0))
			return samurai_plan.get("cell", record.current_cell)
		"wanderer":
			var visited_ticks := _visited_ticks_lookup(record.behavior_state.get("visited_ticks", []))
			var wanderer_plan: Dictionary = EnemyBehaviorSystemsScript.choose_wanderer_plan(
				record.current_cell,
				int(record.behavior_state.get("facing_index", record.config_int("facing_index", 2))),
				record.config_int("behavior_seed", 0),
				int(record.behavior_state.get("decision_count", 0)),
				visited_ticks,
				blocked_lookup,
				func(direction_index: int, occupied: Dictionary) -> bool:
					var target_cell: Vector2i = record.current_cell + _rotation_direction(direction_index)
					return _can_record_enter(record, target_cell, occupied, board_state)
			)
			var next_facing := int(wanderer_plan.get("facing_index", 2))
			var next_cell: Vector2i = wanderer_plan.get("cell", record.current_cell)
			var visit_tick := int(record.behavior_state.get("visit_tick", 0)) + 1
			record.behavior_state["facing_index"] = next_facing
			record.behavior_state["decision_count"] = int(record.behavior_state.get("decision_count", 0)) + 1
			record.behavior_state["visit_tick"] = visit_tick
			if next_cell != record.current_cell:
				visited_ticks[next_cell] = visit_tick
			record.behavior_state["visited_ticks"] = _visited_ticks_snapshot(visited_ticks)
			return next_cell
		"stationary_blocker":
			return record.current_cell
		_:
			return record.current_cell


static func _can_record_enter(record, target_cell: Vector2i, occupied_lookup: Dictionary, board_state) -> bool:
	if not board_state.can_enemy_step(record.current_cell, target_cell):
		return false
	return not occupied_lookup.has(target_cell)


static func _update_post_move_state(record, previous_cell: Vector2i, next_cell: Vector2i) -> void:
	if _scene_family(record) != "samurai":
		return
	var direction: Vector2i = next_cell - previous_cell
	record.behavior_state["facing_index"] = _facing_index_for_direction(
		direction,
		int(record.behavior_state.get("facing_index", record.config_int("facing_index", 2)))
	)
	record.behavior_state["display_facing_index"] = int(record.behavior_state.get("facing_index", record.config_int("facing_index", 2)))


static func _coerce_vector2i_array(raw_value) -> Array[Vector2i]:
	var coerced: Array[Vector2i] = []
	for entry in raw_value:
		if entry is Vector2i:
			coerced.append(entry)
		elif entry is Vector2:
			coerced.append(Vector2i(int(entry.x), int(entry.y)))
		elif entry is Array and entry.size() >= 2:
			coerced.append(Vector2i(int(entry[0]), int(entry[1])))
	return coerced


static func _rotation_direction(direction_index: int) -> Vector2i:
	var directions: Array[Vector2i] = [Vector2i.UP, Vector2i.RIGHT, Vector2i.DOWN, Vector2i.LEFT]
	return directions[direction_index]


static func _facing_index_for_direction(direction: Vector2i, fallback: int) -> int:
	var directions: Array[Vector2i] = [Vector2i.UP, Vector2i.RIGHT, Vector2i.DOWN, Vector2i.LEFT]
	for index in range(directions.size()):
		if directions[index] == direction:
			return index
	return fallback


static func _visited_ticks_lookup(raw_entries) -> Dictionary:
	var visited: Dictionary = {}
	for entry in raw_entries:
		if not entry is Dictionary:
			continue
		var cell = entry.get("cell", Vector2i.ZERO)
		if cell is Vector2:
			cell = Vector2i(int(cell.x), int(cell.y))
		elif cell is Array and cell.size() >= 2:
			cell = Vector2i(int(cell[0]), int(cell[1]))
		visited[cell] = int(entry.get("tick", 0))
	return visited


static func _visited_ticks_snapshot(visited_lookup: Dictionary) -> Array[Dictionary]:
	var entries: Array[Dictionary] = []
	for cell in visited_lookup.keys():
		entries.append({
			"cell": cell,
			"tick": int(visited_lookup[cell]),
		})
	entries.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		var cell_a: Vector2i = a.get("cell", Vector2i.ZERO)
		var cell_b: Vector2i = b.get("cell", Vector2i.ZERO)
		if cell_a.y == cell_b.y:
			return cell_a.x < cell_b.x
		return cell_a.y < cell_b.y
	)
	return entries
