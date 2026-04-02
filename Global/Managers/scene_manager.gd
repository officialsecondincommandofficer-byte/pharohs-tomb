extends Node

var current_scene: Node = null

func goto_scene(path: String):
	_deferred_goto_scene.call_deferred(path)

func _deferred_goto_scene(path: String):
	if current_scene:
		current_scene.queue_free()

	var s = ResourceLoader.load(path)
	current_scene = s.instantiate()
	get_tree().root.add_child(current_scene)
	get_tree().current_scene = current_scene

	# 🔑 Connect all signals automatically
	_connect_scene_signals(current_scene)


func load_character(character_path: String, spawn_point: Marker3D):
	if not current_scene:
		push_error("No active scene loaded!")
		return null

	var char_scene = ResourceLoader.load(character_path)
	if not char_scene:
		push_error("Character scene not found: %s" % character_path)
		return null

	var character = char_scene.instantiate()
	character.global_transform = spawn_point.global_transform
	current_scene.add_child(character)
	return character


func set_scene(new_current_scene: Node):
	current_scene = new_current_scene
	_connect_scene_signals(current_scene)


# 🔑 Generic signal connector
func _connect_scene_signals(scene: Node):
	# Connect start_game if the scene has it
	if scene.has_signal("start_game"):
		print("in connect scene signals")
		if not scene.is_connected("start_game", Callable(self, "_on_start_game")):
			print("connecting")
			scene.connect("start_game", Callable(self, "_on_start_game"))

	# Connect quit_game if the scene has it
	if scene.has_signal("quit_game"):
		if not scene.is_connected("quit_game", Callable(self, "_on_scene_signal")):
			scene.connect("quit_game", Callable(self, "_on_scene_signal"))


func _on_start_game():
	goto_scene("res://src/Stages/TrainingGround/TrainingGround.tscn")

# 🔑 Generic handler for all signals
func _on_scene_signal(signal_name: String, args = []):
	print("Scene emitted signal: ", signal_name, " with args: ", args)

	match signal_name:
		"start_game":
			print("Going and Getting Training stage")
			goto_scene("res://src/stages/TrainingStage.tscn")
		"open_options":
			goto_scene("res://src/ui/OptionsMenu.tscn")
		"quit_game":
			get_tree().quit()
		_:
			print("Unhandled signal: ", signal_name)
