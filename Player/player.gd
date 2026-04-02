extends CharacterBody2D

signal turn_finished(turn_result)

@export var move_duration: float = 0.14
@onready var anim: AnimatedSprite2D = $AnimatedSprite2D

var board_state
var current_cell: Vector2i = Vector2i.ZERO
var input_enabled := false
var inventory: Array[String] = []


func setup_floor(next_board_state) -> void:
	board_state = next_board_state
	current_cell = board_state.player_spawn
	position = board_state.to_world(current_cell)
	inventory.clear()
	input_enabled = true
	_play_idle()


func set_input_enabled(value: bool) -> void:
	input_enabled = value


func get_current_cell() -> Vector2i:
	return current_cell


func has_key() -> bool:
	return inventory.has("key")


func get_inventory_snapshot() -> Array[String]:
	return inventory.duplicate()


func collect_item(item_id: String) -> void:
	inventory.append(item_id)


func _unhandled_input(event: InputEvent) -> void:
	if not input_enabled or board_state == null:
		return

	if event.is_action_pressed("ui_left"):
		request_turn_action({"type": "move", "direction": Vector2i.LEFT})
	elif event.is_action_pressed("ui_right"):
		request_turn_action({"type": "move", "direction": Vector2i.RIGHT})
	elif event.is_action_pressed("ui_up"):
		request_turn_action({"type": "move", "direction": Vector2i.UP})
	elif event.is_action_pressed("ui_down"):
		request_turn_action({"type": "move", "direction": Vector2i.DOWN})
	elif event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_SPACE:
			request_turn_action({"type": "wait"})
		elif event.keycode == KEY_1:
			request_turn_action({"type": "use_item"})


func request_turn_action(action_data: Dictionary) -> void:
	if not input_enabled or board_state == null:
		return

	var action_type: String = String(action_data.get("type", ""))
	var result: Dictionary = {
		"action_type": action_type,
		"consumed_turn": false,
		"previous_cell": current_cell,
		"new_cell": current_cell,
		"blocked": false,
		"used_item": "",
	}

	match action_type:
		"move":
			var direction: Vector2i = action_data.get("direction", Vector2i.ZERO)
			var target_cell: Vector2i = current_cell + direction
			if not board_state.can_step(current_cell, target_cell):
				result["blocked"] = true
				return
			current_cell = target_cell
			result["new_cell"] = current_cell
			result["consumed_turn"] = true
			_update_facing(direction)
			await _animate_to_world_position(board_state.to_world(current_cell))
			_play_idle()
		"wait":
			result["consumed_turn"] = true
			_play_idle()
		"use_item":
			var usable_item := _get_first_usable_item()
			if usable_item.is_empty():
				return
			inventory.erase(usable_item)
			result["consumed_turn"] = true
			result["used_item"] = usable_item
			_play_idle()
		_:
			return

	input_enabled = false
	turn_finished.emit(result)


func _animate_to_world_position(target_position: Vector2) -> void:
	var tween: Tween = create_tween()
	tween.tween_property(self, "position", target_position, move_duration).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	await tween.finished


func _get_first_usable_item() -> String:
	for item_id in inventory:
		if item_id != "key":
			return item_id
	return ""


func _update_facing(direction: Vector2i) -> void:
	if direction.x > 0:
		anim.play("walk_right")
	elif direction.x < 0:
		anim.play("walk_left")
	elif direction.y > 0:
		anim.play("walk_downward")
	elif direction.y < 0:
		anim.play("walk_upward")


func _play_idle() -> void:
	anim.stop()
	anim.frame = 1
