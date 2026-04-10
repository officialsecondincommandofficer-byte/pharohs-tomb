extends Node

const MazeSaveServiceScript = preload("res://MazeGenerator/maze_save_service.gd")

var game_camera: Camera2D
var maze_generator: Node
var tile_map: Node
var fog_of_war: Node2D
var player: CharacterBody2D
var enemy_manager: Node2D
var hud: CanvasLayer

var board_state: MazeData
var move_count := 0
var game_over := false
var input_locked := false
var replaying_solution := false
var _state_history: Array[Dictionary] = []
var _maze_save_service


func bootstrap(system_refs: Dictionary) -> void:
	print("[Startup] GameManager.bootstrap begin")
	game_camera = system_refs["camera"]
	maze_generator = system_refs["maze_generator"]
	tile_map = system_refs["tile_map"]
	fog_of_war = system_refs["fog_of_war"]
	player = system_refs["player"]
	enemy_manager = system_refs["enemy_manager"]
	hud = system_refs["hud"]

	player.action_requested.connect(_on_player_action_requested)
	get_viewport().size_changed.connect(_refresh_camera)
	_maze_save_service = MazeSaveServiceScript.new()
	print("[Startup] GameManager.bootstrap systems connected")

	restart_run()
	print("[Startup] GameManager.bootstrap end")


func restart_run() -> void:
	if input_locked:
		print("[Startup] GameManager.restart_run skipped because input is locked")
		return

	print("[Startup] GameManager.restart_run begin")
	var restart_started_ms := Time.get_ticks_msec()
	board_state = maze_generator.generate_floor()
	var generation_elapsed_ms := Time.get_ticks_msec() - restart_started_ms
	if board_state == null:
		push_error("[Startup] GameManager.restart_run maze generation returned null after %d ms" % generation_elapsed_ms)
		return
	print(
		"[Startup] GameManager.restart_run generated board in %d ms (%dx%d %s %s)" % [
			generation_elapsed_ms,
			board_state.width,
			board_state.height,
			board_state.size_category,
			board_state.difficulty_category,
		]
	)
	move_count = 0
	game_over = false
	input_locked = false
	replaying_solution = false
	_state_history.clear()

	tile_map.render_board(board_state, true)
	fog_of_war.setup_floor(board_state)
	player.setup_floor(board_state)
	enemy_manager.setup_floor(board_state)
	_state_history.append(_snapshot_state("start"))

	_refresh_camera()
	_refresh_visibility()
	_update_hud("In progress")
	hud.set_message(_controls_message())
	player.set_input_enabled(true)
	print("[Startup] GameManager.restart_run end")


func handle_global_action(action_name: String) -> void:
	match action_name:
		"reroll":
			restart_run()
		"reset":
			reset_current_board()
		"undo":
			undo_last_turn()
		"show_solution":
			_start_solution_replay()
		"save_current_maze":
			_save_current_maze()


func reset_current_board() -> void:
	if board_state == null or input_locked:
		return

	move_count = 0
	game_over = false
	replaying_solution = false
	_state_history.clear()
	player.set_cell_immediate(board_state.player_spawn)
	enemy_manager.set_cell_immediate(board_state.minotaur_spawn)
	_state_history.append(_snapshot_state("start"))
	_refresh_visibility()
	_update_hud("In progress")
	hud.set_message("Board reset. %s" % _controls_message())
	player.set_input_enabled(true)


func undo_last_turn() -> void:
	if input_locked or _state_history.size() <= 1:
		return

	_state_history.pop_back()
	var snapshot: Dictionary = _state_history.back()
	move_count = max(_state_history.size() - 1, 0)
	game_over = false
	replaying_solution = false
	player.set_cell_immediate(snapshot["player"])
	enemy_manager.set_cell_immediate(snapshot["minotaur"])
	_refresh_visibility()
	_update_hud("In progress")
	hud.set_message("Move undone. %s" % _controls_message())
	player.set_input_enabled(true)


func _on_player_action_requested(action_name: String) -> void:
	if input_locked or game_over or replaying_solution:
		return
	_resolve_player_action.call_deferred(action_name, false)


func _start_solution_replay() -> void:
	if board_state == null or input_locked or board_state.solution_actions.is_empty():
		return
	_run_solution_replay.call_deferred()


func _save_current_maze() -> void:
	if board_state == null:
		hud.set_message("There is no active maze to save.")
		return
	if _maze_save_service == null:
		hud.set_message("Maze saving is unavailable right now.")
		return

	var save_result: Dictionary = _maze_save_service.save_board(board_state)
	if not bool(save_result.get("success", false)):
		hud.set_message(String(save_result.get("message", "Could not save the current maze.")))
		return

	var file_name := String(save_result.get("file_name", ""))
	hud.set_message("Maze saved to user://saved_mazes/%s. %s" % [file_name, _controls_message()])


func _run_solution_replay() -> void:
	reset_current_board()
	replaying_solution = true
	input_locked = true
	player.set_input_enabled(false)
	hud.set_message("Showing solution...")
	await get_tree().create_timer(0.1).timeout

	for action in board_state.solution_actions:
		await _resolve_player_action(action, true)
		if game_over:
			break
		await get_tree().create_timer(0.1).timeout

	replaying_solution = false
	input_locked = false
	player.set_input_enabled(not game_over)
	if game_over and player.get_current_cell() == board_state.exit_cell:
		hud.set_message("SOLUTION GIVEN")


func _resolve_player_action(action_name: String, from_replay: bool) -> void:
	if board_state == null:
		return
	if input_locked and not from_replay:
		return

	var current_player: Vector2i = player.get_current_cell()
	var next_player: Vector2i = board_state.apply_action(current_player, action_name)
	if next_player == current_player and action_name != "skip":
		if not from_replay:
			hud.set_message("That move is blocked.")
		return

	if not from_replay:
		input_locked = true
		player.set_input_enabled(false)

	if next_player != current_player:
		await player.move_to_cell(next_player)
	else:
		player.set_cell_immediate(current_player)

	await enemy_manager.begin_enemy_phase(next_player)
	move_count += 1
	_state_history.append(_snapshot_state(action_name))
	_refresh_visibility()

	var status_text := "In progress"
	if enemy_manager.get_current_cell() == next_player:
		game_over = true
		status_text = "You lose"
	elif next_player == board_state.exit_cell:
		game_over = true
		status_text = "You win"

	_update_hud(status_text)

	if game_over:
		if from_replay and next_player == board_state.exit_cell:
			hud.set_message("SOLUTION GIVEN")
		elif next_player == board_state.exit_cell:
			hud.set_message("YOU WIN!")
		else:
			hud.set_message("YOU LOSE!")
	else:
		if not from_replay:
			hud.set_message(_controls_message())

	if not from_replay:
		input_locked = false
		player.set_input_enabled(not game_over)


func _snapshot_state(action_name: String) -> Dictionary:
	return {
		"action": action_name,
		"player": player.get_current_cell(),
		"minotaur": enemy_manager.get_current_cell(),
	}


func _refresh_visibility() -> void:
	if board_state == null:
		return

	var visible_cells: Array[Vector2i] = fog_of_war.update_visibility(
		player.get_current_cell(),
		max(board_state.width, board_state.height),
		true
	)
	enemy_manager.update_visibility(visible_cells)


func _refresh_camera() -> void:
	if board_state == null or game_camera == null:
		return

	var board_pixel_size: Vector2 = Vector2(
		board_state.width * board_state.cell_size,
		board_state.height * board_state.cell_size
	) + Vector2.ONE * board_state.cell_size * 2.0
	var board_center := Vector2(
		board_state.width * board_state.cell_size * 0.5,
		board_state.height * board_state.cell_size * 0.5
	)
	var viewport_size := get_viewport().get_visible_rect().size
	var width_scale: float = (viewport_size.x * 0.82) / max(board_pixel_size.x, 1.0)
	var height_scale: float = (viewport_size.y * 0.72) / max(board_pixel_size.y, 1.0)
	var presentation_scale: float = clamp(min(width_scale, height_scale), 1.5, 4.0)

	game_camera.position = board_center
	game_camera.zoom = Vector2.ONE * presentation_scale


func _update_hud(status_text: String) -> void:
	hud.update_state({
		"grid_width": board_state.width,
		"grid_height": board_state.height,
		"size_category": board_state.size_category,
		"difficulty": board_state.difficulty_category,
		"wall_density": board_state.wall_density,
		"moves_taken": move_count,
		"solution_total_steps": board_state.solution_total_steps,
		"seed_id": _get_seed_id(),
		"status": status_text,
	})


func _controls_message() -> String:
	return "Arrows move, Space waits, Shift undoes, Backspace resets, P shows the solution, K saves, R rerolls."


func _get_seed_id() -> String:
	if board_state == null:
		return "N/A"
	if board_state.saved_at_unix > 0:
		return str(board_state.saved_at_unix)
	if board_state.maze_key.has("seed"):
		return str(board_state.maze_key["seed"])
	if not board_state.generation_profile_id.is_empty():
		return board_state.generation_profile_id
	return "N/A"
