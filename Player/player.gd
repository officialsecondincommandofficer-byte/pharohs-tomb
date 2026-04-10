extends CharacterBody2D

signal action_requested(action_name)

@export var move_duration: float = 0.14
@onready var anim: AnimatedSprite2D = $AnimatedSprite2D

var board_state: MazeData
var current_cell: Vector2i = Vector2i.ZERO
var input_enabled := false


func setup_floor(next_board_state: MazeData) -> void:
	board_state = next_board_state
	set_cell_immediate(board_state.player_spawn)
	input_enabled = true


func set_input_enabled(value: bool) -> void:
	input_enabled = value


func get_current_cell() -> Vector2i:
	return current_cell


func set_cell_immediate(cell: Vector2i) -> void:
	current_cell = cell
	position = board_state.to_world(current_cell)
	_play_idle()


func move_to_cell(cell: Vector2i) -> void:
	var direction: Vector2i = cell - current_cell
	current_cell = cell
	if direction != Vector2i.ZERO:
		_update_facing(direction)
		await _animate_to_world_position(board_state.to_world(current_cell))
	_play_idle()


func _unhandled_input(event: InputEvent) -> void:
	if not input_enabled or board_state == null:
		return

	if event.is_action_pressed("ui_left"):
		action_requested.emit("left")
	elif event.is_action_pressed("ui_right"):
		action_requested.emit("right")
	elif event.is_action_pressed("ui_up"):
		action_requested.emit("up")
	elif event.is_action_pressed("ui_down"):
		action_requested.emit("down")
	elif event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_SPACE:
		action_requested.emit("skip")


func _animate_to_world_position(target_position: Vector2) -> void:
	var tween: Tween = create_tween()
	tween.tween_property(self, "position", target_position, move_duration).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	await tween.finished


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
