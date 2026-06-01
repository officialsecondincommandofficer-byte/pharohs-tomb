extends RefCounted
class_name EnemyBehaviorSystems

const AStarChaserLogicScript := preload("res://EnemyManager/AStarChaser/astar_chaser_logic.gd")
const ChaserLogicScript := preload("res://EnemyManager/chaser_logic.gd")

const PATROL_MODE_LOOP := "loop"
const ROTATION_DIRECTIONS: Array[Vector2i] = [
	Vector2i.UP,
	Vector2i.RIGHT,
	Vector2i.DOWN,
	Vector2i.LEFT,
]
const SAMURAI_CHARGE_DELAYS: Array[int] = [3, 2, 1]


static func choose_chaser_target(
	current_cell: Vector2i,
	player_cell: Vector2i,
	occupied_lookup: Dictionary,
	board_state,
	movement_family: String,
	move_priority: String
) -> Vector2i:
	if movement_family == "astar":
		return AStarChaserLogicScript.choose_astar_step(
			current_cell,
			player_cell,
			occupied_lookup,
			board_state
		)
	return ChaserLogicScript.choose_greedy_step(
		current_cell,
		player_cell,
		occupied_lookup,
		board_state,
		move_priority
	)


static func choose_minotaur_target(
	current_cell: Vector2i,
	player_cell: Vector2i,
	board_state,
	move_priority: String = "horizontal"
) -> Vector2i:
	var horizontal_first: bool = move_priority != "vertical"
	if horizontal_first:
		var horizontal_step: Vector2i = _axis_step_toward(current_cell, player_cell, true)
		if horizontal_step != current_cell and board_state.can_enemy_step(current_cell, horizontal_step):
			return horizontal_step
		var vertical_step: Vector2i = _axis_step_toward(current_cell, player_cell, false)
		if vertical_step != current_cell and board_state.can_enemy_step(current_cell, vertical_step):
			return vertical_step
	else:
		var vertical_step: Vector2i = _axis_step_toward(current_cell, player_cell, false)
		if vertical_step != current_cell and board_state.can_enemy_step(current_cell, vertical_step):
			return vertical_step
		var horizontal_step: Vector2i = _axis_step_toward(current_cell, player_cell, true)
		if horizontal_step != current_cell and board_state.can_enemy_step(current_cell, horizontal_step):
			return horizontal_step
	return current_cell


static func choose_patroller_target(
	current_cell: Vector2i,
	patrol_route: Array[Vector2i],
	patrol_index: int,
	patrol_direction: int,
	patrol_mode: String,
	occupied_lookup: Dictionary,
	can_enter: Callable
) -> Dictionary:
	if patrol_route.size() <= 1:
		return {
			"cell": current_cell,
			"patrol_index": patrol_index,
			"patrol_direction": patrol_direction,
		}

	var next_index := patrol_index + patrol_direction
	var next_direction := patrol_direction
	if patrol_mode == PATROL_MODE_LOOP:
		next_index = (patrol_index + 1) % patrol_route.size()
	else:
		if next_index < 0 or next_index >= patrol_route.size():
			next_direction *= -1
			next_index = patrol_index + next_direction

	var target_cell: Vector2i = patrol_route[next_index]
	if not bool(can_enter.call(target_cell, occupied_lookup)):
		if patrol_mode == PATROL_MODE_LOOP:
			return {
				"cell": current_cell,
				"patrol_index": patrol_index,
				"patrol_direction": patrol_direction,
			}
		next_direction *= -1
		next_index = patrol_index + next_direction
		if next_index < 0 or next_index >= patrol_route.size():
			return {
				"cell": current_cell,
				"patrol_index": patrol_index,
				"patrol_direction": next_direction,
			}
		target_cell = patrol_route[next_index]
		if not bool(can_enter.call(target_cell, occupied_lookup)):
			return {
				"cell": current_cell,
				"patrol_index": patrol_index,
				"patrol_direction": next_direction,
			}

	return {
		"cell": target_cell,
		"patrol_index": next_index,
		"patrol_direction": next_direction,
	}


static func choose_wanderer_plan(
	current_cell: Vector2i,
	facing_index: int,
	behavior_seed: int,
	decision_count: int,
	visited_ticks: Dictionary,
	occupied_lookup: Dictionary,
	can_move: Callable
) -> Dictionary:
	var forward := facing_index
	var preferred := [
		forward,
		posmod(forward - 1, ROTATION_DIRECTIONS.size()),
		posmod(forward + 1, ROTATION_DIRECTIONS.size()),
	]
	var preferred_legal: Array[int] = []
	for direction_index in preferred:
		if bool(can_move.call(direction_index, occupied_lookup)):
			preferred_legal.append(direction_index)

	if not preferred_legal.is_empty():
		var chosen_direction := _choose_wanderer_direction(
			current_cell,
			preferred_legal,
			behavior_seed,
			decision_count,
			visited_ticks
		)
		return {
			"cell": current_cell + ROTATION_DIRECTIONS[chosen_direction],
			"facing_index": chosen_direction,
		}

	var back := posmod(forward + 2, ROTATION_DIRECTIONS.size())
	if bool(can_move.call(back, occupied_lookup)):
		return {
			"cell": current_cell + ROTATION_DIRECTIONS[back],
			"facing_index": back,
		}

	return {
		"cell": current_cell,
		"facing_index": facing_index,
	}


static func choose_samurai_turn(
	current_cell: Vector2i,
	player_cell: Vector2i,
	occupied_lookup: Dictionary,
	board_state,
	behavior_state
) -> Dictionary:
	return choose_samurai_turn_state(
		current_cell,
		player_cell,
		occupied_lookup,
		board_state,
		int(behavior_state.facing_index),
		int(behavior_state.attack_phase),
		int(behavior_state.turns_until_dash)
	)


static func choose_samurai_turn_state(
	current_cell: Vector2i,
	player_cell: Vector2i,
	occupied_lookup: Dictionary,
	board_state,
	facing_index: int,
	attack_phase: int,
	turns_until_dash_state: int
) -> Dictionary:
	if attack_phase == -1:
		var rotated_facing: int = (facing_index + 1) % ROTATION_DIRECTIONS.size()
		var triggered: bool = _samurai_can_see_player(current_cell, player_cell, rotated_facing)
		return {
			"cell": current_cell,
			"facing_index": rotated_facing,
			"display_facing_index": rotated_facing,
			"attack_phase": 0 if triggered else -1,
			"turns_until_dash": SAMURAI_CHARGE_DELAYS[0] if triggered else 0,
		}

	var turns_until_dash: int = turns_until_dash_state - 1
	var preview_dash_target: Vector2i = _choose_samurai_dash_target(
		current_cell,
		player_cell,
		occupied_lookup,
		board_state,
		facing_index
	)
	var preview_facing: int = _direction_facing_index(preview_dash_target - current_cell, facing_index)
	if turns_until_dash > 0:
		return {
			"cell": current_cell,
			"facing_index": facing_index,
			"display_facing_index": preview_facing,
			"attack_phase": attack_phase,
			"turns_until_dash": turns_until_dash,
		}

	var dash_target := _choose_samurai_dash_target(
		current_cell,
		player_cell,
		occupied_lookup,
		board_state,
		facing_index
	)
	var next_phase: int = attack_phase + 1
	if next_phase >= SAMURAI_CHARGE_DELAYS.size():
		return {
			"cell": dash_target,
			"facing_index": facing_index,
			"display_facing_index": _direction_facing_index(dash_target - current_cell, facing_index),
			"attack_phase": -1,
			"turns_until_dash": 0,
		}

	return {
		"cell": dash_target,
		"facing_index": facing_index,
		"display_facing_index": _direction_facing_index(dash_target - current_cell, facing_index),
		"attack_phase": next_phase,
		"turns_until_dash": SAMURAI_CHARGE_DELAYS[next_phase],
	}


static func _choose_wanderer_direction(
	current_cell: Vector2i,
	preferred_legal: Array[int],
	behavior_seed: int,
	decision_count: int,
	visited_ticks: Dictionary
) -> int:
	var oldest_visit_tick := 2147483647
	for direction_index in preferred_legal:
		var target_cell := current_cell + ROTATION_DIRECTIONS[direction_index]
		oldest_visit_tick = mini(oldest_visit_tick, _last_visit_tick(visited_ticks, target_cell))
	var candidate_directions: Array[int] = []
	for direction_index in preferred_legal:
		var target_cell := current_cell + ROTATION_DIRECTIONS[direction_index]
		if _last_visit_tick(visited_ticks, target_cell) == oldest_visit_tick:
			candidate_directions.append(direction_index)
	var choice_index := _seeded_choice_index(current_cell, behavior_seed, decision_count, candidate_directions.size())
	return candidate_directions[choice_index]


static func _seeded_choice_index(current_cell: Vector2i, behavior_seed: int, decision_count: int, option_count: int) -> int:
	var mixed: int = int(
		((behavior_seed * 1103515245) + (decision_count * 12345) + (current_cell.x * 92821) + (current_cell.y * 68917))
		& 0x7fffffff
	)
	return posmod(mixed, option_count)


static func _last_visit_tick(visited_ticks: Dictionary, cell: Vector2i) -> int:
	if visited_ticks.has(cell):
		return int(visited_ticks[cell])
	return -1


static func _samurai_can_see_player(current_cell: Vector2i, player_cell: Vector2i, facing_index: int) -> bool:
	var delta: Vector2i = player_cell - current_cell
	var facing: Vector2i = ROTATION_DIRECTIONS[facing_index]
	if facing.x != 0:
		return delta.y == 0 and sign(delta.x) == facing.x and delta.x != 0
	return delta.x == 0 and sign(delta.y) == facing.y and delta.y != 0


static func _choose_samurai_dash_target(
	current_cell: Vector2i,
	player_cell: Vector2i,
	occupied_lookup: Dictionary,
	board_state,
	facing_index: int
) -> Vector2i:
	var delta: Vector2i = player_cell - current_cell
	if delta == Vector2i.ZERO:
		return current_cell
	var use_vertical: bool = abs(delta.y) > abs(delta.x)
	if abs(delta.x) == abs(delta.y):
		var facing: Vector2i = ROTATION_DIRECTIONS[facing_index]
		use_vertical = facing.y != 0 and delta.y != 0
	var target_cell := current_cell
	if use_vertical and delta.y != 0:
		target_cell = Vector2i(current_cell.x, player_cell.y)
	elif delta.x != 0:
		target_cell = Vector2i(player_cell.x, current_cell.y)
	elif delta.y != 0:
		target_cell = Vector2i(current_cell.x, player_cell.y)
	if not board_state.is_in_bounds(target_cell):
		return current_cell
	if occupied_lookup.has(target_cell):
		return current_cell
	return target_cell


static func _axis_step_toward(current_cell: Vector2i, target_cell: Vector2i, horizontal: bool) -> Vector2i:
	if horizontal:
		if target_cell.x > current_cell.x:
			return current_cell + Vector2i.RIGHT
		if target_cell.x < current_cell.x:
			return current_cell + Vector2i.LEFT
		return current_cell
	if target_cell.y < current_cell.y:
		return current_cell + Vector2i.UP
	if target_cell.y > current_cell.y:
		return current_cell + Vector2i.DOWN
	return current_cell


static func _direction_facing_index(direction: Vector2i, fallback: int) -> int:
	if direction == Vector2i.ZERO:
		return fallback
	if abs(direction.x) >= abs(direction.y):
		return 1 if direction.x > 0 else 3
	return 2 if direction.y > 0 else 0
