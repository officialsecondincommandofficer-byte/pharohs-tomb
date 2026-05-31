extends "res://EnemyManager/enemy_base.gd"

const SamuraiBehaviorStateScript = preload("res://EnemyManager/Samurai/samurai_behavior_state.gd")
const ROTATION_DIRECTIONS: Array[Vector2i] = [
	Vector2i.UP,
	Vector2i.RIGHT,
	Vector2i.DOWN,
	Vector2i.LEFT,
]
const CHARGE_DELAYS: Array[int] = [3, 2, 1]

var behavior_state = SamuraiBehaviorStateScript.new()


func _ready() -> void:
	enemy_type = "samurai"
	super._ready()
	_apply_facing()


func configure(spawn_data: Dictionary, next_board_state) -> void:
	behavior_state = SamuraiBehaviorStateScript.new()
	behavior_state.facing_index = posmod(int(spawn_data.get("facing_index", behavior_state.facing_index)), ROTATION_DIRECTIONS.size())
	super.configure(spawn_data, next_board_state)
	_apply_facing()


func choose_target_cell(player_cell: Vector2i, occupied_lookup: Dictionary) -> Vector2i:
	if behavior_state.attack_phase == -1:
		_rotate_clockwise()
		if _can_see_player(player_cell):
			behavior_state.attack_phase = 0
			behavior_state.turns_until_dash = CHARGE_DELAYS[behavior_state.attack_phase]
		return current_cell

	behavior_state.turns_until_dash -= 1
	if behavior_state.turns_until_dash > 0:
		return current_cell

	var dash_target: Vector2i = _choose_dash_target(player_cell, occupied_lookup)
	_advance_attack_cycle()
	return dash_target


func _build_behavior_state_snapshot() -> Dictionary:
	return behavior_state.to_dictionary()


func _restore_behavior_state_snapshot(state: Dictionary) -> void:
	behavior_state.from_dictionary(state)
	behavior_state.facing_index = posmod(behavior_state.facing_index, ROTATION_DIRECTIONS.size())
	_apply_facing()


func _rotate_clockwise() -> void:
	behavior_state.facing_index = (behavior_state.facing_index + 1) % ROTATION_DIRECTIONS.size()
	_apply_facing()


func _apply_facing() -> void:
	_update_facing(ROTATION_DIRECTIONS[behavior_state.facing_index])


func _can_see_player(player_cell: Vector2i) -> bool:
	var delta: Vector2i = player_cell - current_cell
	var facing: Vector2i = ROTATION_DIRECTIONS[behavior_state.facing_index]

	if facing.x != 0:
		return delta.y == 0 and sign(delta.x) == facing.x and delta.x != 0

	return delta.x == 0 and sign(delta.y) == facing.y and delta.y != 0


func _choose_dash_target(player_cell: Vector2i, occupied_lookup: Dictionary) -> Vector2i:
	var delta: Vector2i = player_cell - current_cell
	if delta == Vector2i.ZERO:
		return current_cell

	var use_vertical: bool = abs(delta.y) > abs(delta.x)
	if abs(delta.x) == abs(delta.y):
		var facing: Vector2i = ROTATION_DIRECTIONS[behavior_state.facing_index]
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


func _advance_attack_cycle() -> void:
	behavior_state.attack_phase += 1
	if behavior_state.attack_phase >= CHARGE_DELAYS.size():
		behavior_state.attack_phase = -1
		behavior_state.turns_until_dash = 0
		return

	behavior_state.turns_until_dash = CHARGE_DELAYS[behavior_state.attack_phase]
