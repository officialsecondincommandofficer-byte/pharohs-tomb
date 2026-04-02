extends Node

signal turn_started(turn_number, turns_remaining)
signal turn_resolved(turn_result)
signal floor_cleared(floor_index)
signal player_died(reason)
signal run_finished(did_win)

var game_camera: Camera2D
var maze_generator: Node
var tile_map: Node
var fog_of_war: Node2D
var player: CharacterBody2D
var enemy_manager: Node2D
var item_layer: Node2D
var hud: CanvasLayer

var board_state
var current_floor := 1
var total_floors := 1
var turns_taken := 0
var turns_remaining := 0
var exit_unlocked := false
var freeze_turns_remaining := 0
var torch_turns_remaining := 0
var compass_turns_remaining := 0
var run_complete := false


func bootstrap(system_refs: Dictionary) -> void:
	game_camera = system_refs["camera"]
	maze_generator = system_refs["maze_generator"]
	tile_map = system_refs["tile_map"]
	fog_of_war = system_refs["fog_of_war"]
	player = system_refs["player"]
	enemy_manager = system_refs["enemy_manager"]
	item_layer = system_refs["item_layer"]
	hud = system_refs["hud"]

	player.turn_finished.connect(_on_player_turn_finished)
	enemy_manager.enemy_phase_finished.connect(_on_enemy_phase_finished)
	item_layer.item_collected.connect(_on_item_collected)
	get_viewport().size_changed.connect(_refresh_camera)

	restart_run()


func restart_run() -> void:
	current_floor = 1
	run_complete = false
	_load_floor(current_floor)


func is_run_complete() -> bool:
	return run_complete


func _load_floor(floor_index: int) -> void:
	board_state = maze_generator.generate_floor(floor_index)
	turns_taken = 0
	turns_remaining = board_state.turn_limit
	exit_unlocked = false
	freeze_turns_remaining = 0
	torch_turns_remaining = 0
	compass_turns_remaining = 0

	tile_map.render_board(board_state, exit_unlocked)
	item_layer.setup_floor(board_state)
	player.setup_floor(board_state)
	enemy_manager.setup_floor(board_state)
	fog_of_war.setup_floor(board_state)

	_refresh_camera()
	_refresh_visibility()
	_update_hud()
	hud.set_message("Arrow keys move, Space waits, 1 uses the first item, R restarts.")
	player.set_input_enabled(true)
	turn_started.emit(turns_taken, turns_remaining)


func _on_player_turn_finished(turn_result: Dictionary) -> void:
	if run_complete:
		return

	if not turn_result.get("consumed_turn", false):
		player.set_input_enabled(true)
		return

	var used_item := String(turn_result.get("used_item", ""))
	if not used_item.is_empty():
		_apply_item_effect(used_item)

	var player_cell: Vector2i = player.get_current_cell()
	if enemy_manager.is_cell_occupied(player_cell):
		_handle_loss("An enemy caught you.")
		return

	item_layer.collect_item_at(player_cell)

	turns_taken += 1
	turns_remaining -= 1

	if exit_unlocked and player_cell == board_state.exit_cell:
		_handle_floor_clear()
		return

	if turns_remaining <= 0:
		_handle_loss("You ran out of turns.")
		return

	turn_resolved.emit(turn_result)

	if freeze_turns_remaining > 0:
		freeze_turns_remaining -= 1
		_on_enemy_phase_finished([])
		return

	enemy_manager.begin_enemy_phase(player_cell)


func _on_enemy_phase_finished(enemy_results: Array) -> void:
	if run_complete:
		return

	for result in enemy_results:
		if result.get("contact_player", false):
			_handle_loss("An enemy moved onto your tile.")
			return

	if enemy_manager.is_cell_occupied(player.get_current_cell()):
		_handle_loss("An enemy cornered you.")
		return

	if torch_turns_remaining > 0:
		torch_turns_remaining -= 1
	if compass_turns_remaining > 0:
		compass_turns_remaining -= 1

	_refresh_visibility()
	_update_hud()

	if exit_unlocked and player.get_current_cell() == board_state.exit_cell:
		_handle_floor_clear()
		return

	player.set_input_enabled(true)
	turn_started.emit(turns_taken, turns_remaining)


func _on_item_collected(item_id: String) -> void:
	player.collect_item(item_id)
	if item_id == "key":
		exit_unlocked = true
		tile_map.set_exit_unlocked(true)
		hud.set_message("The exit is unlocked. Reach the gold tile.")
	else:
		hud.set_message("Collected %s." % item_id.capitalize())

	_refresh_visibility()
	_update_hud()


func _apply_item_effect(item_id: String) -> void:
	match item_id:
		"torch":
			torch_turns_remaining = max(torch_turns_remaining, 3)
			hud.set_message("Torch lit. Fog radius increased.")
		"freeze":
			freeze_turns_remaining = max(freeze_turns_remaining, 2)
			hud.set_message("Freeze used. Enemy turns are skipped.")
		"compass":
			compass_turns_remaining = max(compass_turns_remaining, 3)
			hud.set_message("Compass reveals the exit.")
		"extra_turns":
			turns_remaining += 8
			hud.set_message("Extra turns added.")
		_:
			hud.set_message("Used %s." % item_id)

	item_layer.notify_item_used(item_id, {"turns_remaining": turns_remaining})
	_refresh_visibility()
	_update_hud()


func _refresh_visibility() -> void:
	if board_state == null:
		return

	var visibility_radius: int = int(board_state.base_visibility_radius)
	if torch_turns_remaining > 0:
		visibility_radius += board_state.torch_bonus_radius

	var visible_cells: Array[Vector2i] = fog_of_war.update_visibility(
		player.get_current_cell(),
		visibility_radius,
		compass_turns_remaining > 0
	)
	enemy_manager.update_visibility(visible_cells)
	item_layer.update_visibility(visible_cells)


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


func _update_hud() -> void:
	hud.update_state({
		"floor": current_floor,
		"total_floors": total_floors,
		"grid_width": board_state.width,
		"grid_height": board_state.height,
		"wall_density": board_state.wall_density,
		"turns_remaining": turns_remaining,
		"has_key": player.has_key(),
		"inventory": player.get_inventory_snapshot(),
	})


func _handle_floor_clear() -> void:
	run_complete = true
	player.set_input_enabled(false)
	hud.set_message("You escaped floor %d. Press R to restart." % current_floor)
	floor_cleared.emit(current_floor)
	run_finished.emit(true)


func _handle_loss(reason: String) -> void:
	run_complete = true
	player.set_input_enabled(false)
	hud.set_message("%s Press R to restart." % reason)
	player_died.emit(reason)
	run_finished.emit(false)
