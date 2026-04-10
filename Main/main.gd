extends Node2D

@onready var game_manager: Node = $GameManager


func _ready() -> void:
	print("[Startup] Main._ready begin")
	_ensure_global_input_actions()
	print("[Startup] Main input actions ready")
	game_manager.bootstrap({
		"camera": $GameCamera,
		"maze_generator": $MazeGenerator,
		"tile_map": $TileMap,
		"fog_of_war": $FogOfWar,
		"player": $Player,
		"enemy_manager": $EnemyManager,
		"hud": $HUD,
	})
	print("[Startup] Main._ready end")


func _unhandled_input(event: InputEvent) -> void:
	if not (event is InputEventKey and event.pressed and not event.echo):
		return

	match event.keycode:
		KEY_R:
			game_manager.handle_global_action("reroll")
		KEY_BACKSPACE:
			game_manager.handle_global_action("reset")
		KEY_SHIFT:
			game_manager.handle_global_action("undo")
		KEY_P:
			game_manager.handle_global_action("show_solution")
		_:
			if event.is_action_pressed("save_current_maze"):
				game_manager.handle_global_action("save_current_maze")


func _ensure_global_input_actions() -> void:
	_bind_key_action("save_current_maze", KEY_K)


func _bind_key_action(action_name: String, keycode: Key) -> void:
	if not InputMap.has_action(action_name):
		InputMap.add_action(action_name)

	for action_event in InputMap.action_get_events(action_name):
		if action_event is InputEventKey and action_event.physical_keycode == keycode:
			return

	var key_event := InputEventKey.new()
	key_event.keycode = keycode
	key_event.physical_keycode = keycode
	InputMap.action_add_event(action_name, key_event)
