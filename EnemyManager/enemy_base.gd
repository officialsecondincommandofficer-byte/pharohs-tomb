extends CharacterBody2D

@export var enemy_type: String = "enemy"
@export var tint: Color = Color.WHITE
@export var move_duration: float = 0.12

@onready var anim: AnimatedSprite2D = $AnimatedSprite2D

var board_state
var current_cell: Vector2i = Vector2i.ZERO
var patrol_route: Array[Vector2i] = []
var patrol_index := 0
var patrol_direction := 1
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.randomize()
	anim.modulate = tint


func configure(spawn_data: Dictionary, next_board_state) -> void:
	board_state = next_board_state
	enemy_type = String(spawn_data.get("type", enemy_type))
	var next_tint: Color = spawn_data.get("tint", tint)
	tint = next_tint
	current_cell = spawn_data.get("cell", Vector2i.ZERO)
	patrol_route.clear()
	var raw_patrol_route: Array = spawn_data.get("patrol_route", [current_cell])
	for patrol_cell in raw_patrol_route:
		patrol_route.append(patrol_cell)
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
		"previous_cell": current_cell,
		"new_cell": current_cell,
		"contact_player": false,
	}

	if next_cell == current_cell:
		return result

	current_cell = next_cell
	result["new_cell"] = current_cell
	result["contact_player"] = current_cell == player_cell
	_update_facing(current_cell - result["previous_cell"])
	await _animate_to_world_position(board_state.to_world(current_cell))
	return result


func choose_target_cell(_player_cell: Vector2i, _occupied_lookup: Dictionary) -> Vector2i:
	return current_cell


func _can_enter(cell: Vector2i, occupied_lookup: Dictionary) -> bool:
	if not board_state.can_step(current_cell, cell):
		return false
	return not occupied_lookup.has(cell)


func _find_path(start: Vector2i, goal: Vector2i, occupied_lookup: Dictionary) -> Array[Vector2i]:
	var queue: Array[Vector2i] = [start]
	var came_from: Dictionary = {start: start}

	while not queue.is_empty():
		var current: Vector2i = queue.pop_front()
		if current == goal:
			break

		for neighbor in board_state.get_cardinal_neighbors(current):
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
