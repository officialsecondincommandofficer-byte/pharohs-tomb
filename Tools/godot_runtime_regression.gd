extends Node

const MainScene := preload("res://Main/Main.tscn")
const WorldManifestParserScript := preload("res://Worlds/world_manifest_parser.gd")
const WorldLevelDefinitionScript := preload("res://Worlds/world_level_definition.gd")

const SOLVER_TEST_MANIFEST := "res://Resources/Worlds/SolverTestMazes/world_manifest.json"
const ENEMY_RESTORE_LEVEL_ID := "solver_patroller_stationary_wanderer_8x8_b"
const SPAWNER_RESTORE_LEVEL_ID := "solver_escape_zone_two_enemy_12x12_a"

var _failures: Array[String] = []


func _ready() -> void:
	_run.call_deferred()


func _run() -> void:
	var parser = WorldManifestParserScript.new()
	var world = parser.parse_manifest(SOLVER_TEST_MANIFEST)
	if world == null:
		_record_failure("Could not parse solver test world manifest.")
		_finish()
		return

	var enemy_level = _find_level(world.levels, ENEMY_RESTORE_LEVEL_ID)
	var spawner_level = _find_level(world.levels, SPAWNER_RESTORE_LEVEL_ID)
	if enemy_level == null:
		_record_failure("Missing regression level: %s" % ENEMY_RESTORE_LEVEL_ID)
	if spawner_level == null:
		_record_failure("Missing regression level: %s" % SPAWNER_RESTORE_LEVEL_ID)
	if not _failures.is_empty():
		_finish()
		return

	await _run_enemy_restore_regression(world, enemy_level)
	await _run_spawner_restore_regression(world, spawner_level)
	_finish()


func _run_enemy_restore_regression(world, level) -> void:
	var main = await _instantiate_level(world, level)
	if main == null:
		return

	var game_manager = main.get_node("GameManager")
	var initial_snapshot: Dictionary = game_manager.world_runtime_registry.current_snapshot()
	var solution_actions: Array[String] = game_manager.board_state.solution_actions
	if solution_actions.is_empty():
		_record_failure("Enemy regression level has no solution actions: %s" % level.level_id)
		await _cleanup_scene(main)
		return

	await game_manager._resolve_player_action(solution_actions[0], false)
	var moved_snapshot: Dictionary = game_manager.world_runtime_registry.current_snapshot()
	_expect(game_manager.world_runtime_registry.move_count() == 1, "Move count should increment after one action.")
	_expect(moved_snapshot.get("player") != initial_snapshot.get("player"), "Player cell should change after the first enemy regression action.")

	game_manager.handle_global_action("undo")
	await get_tree().process_frame
	var undo_snapshot: Dictionary = game_manager.world_runtime_registry.current_snapshot()
	_expect(undo_snapshot.get("player_state") == initial_snapshot.get("player_state"), "Undo should restore the initial player runtime state.")
	_expect(undo_snapshot.get("enemy_runtime_payload") == initial_snapshot.get("enemy_runtime_payload"), "Undo should restore the initial enemy runtime payload.")
	_expect(game_manager.world_runtime_registry.move_count() == 0, "Undo should restore move count to zero.")

	game_manager.handle_global_action("show_solution")
	await get_tree().process_frame
	var replay_after_undo_finished := await _wait_for_replay_completion(game_manager, 8.0)
	_expect(replay_after_undo_finished, "Replay should still complete after undo restores the runtime snapshot.")
	if replay_after_undo_finished:
		_expect(game_manager.world_runtime_registry.is_game_over(), "Replay after undo should end in a terminal state.")
		_expect(
			game_manager.board_state.is_exit_cell(game_manager.world_runtime_registry.player_cell()),
			"Replay after undo should still finish on a win cell."
		)

	game_manager.handle_global_action("reset")
	await get_tree().process_frame
	var reset_snapshot: Dictionary = game_manager.world_runtime_registry.current_snapshot()
	_expect(reset_snapshot.get("player_state") == initial_snapshot.get("player_state"), "Reset should restore the initial player runtime state.")
	_expect(reset_snapshot.get("enemy_runtime_payload") == initial_snapshot.get("enemy_runtime_payload"), "Reset should restore the initial enemy runtime payload.")
	_expect(game_manager.world_runtime_registry.move_count() == 0, "Reset should restore move count to zero.")

	game_manager.handle_global_action("show_solution")
	await get_tree().process_frame
	var replay_after_reset_finished := await _wait_for_replay_completion(game_manager, 8.0)
	_expect(replay_after_reset_finished, "Replay should complete within the regression timeout after reset.")
	if replay_after_reset_finished:
		_expect(game_manager.world_runtime_registry.is_game_over(), "Replay should end in a terminal state.")
		_expect(
			game_manager.board_state.is_exit_cell(game_manager.world_runtime_registry.player_cell()),
			"Replay after reset should finish on a win cell for the enemy regression level."
		)

	await _cleanup_scene(main)


func _run_spawner_restore_regression(world, level) -> void:
	var main = await _instantiate_level(world, level)
	if main == null:
		return

	var game_manager = main.get_node("GameManager")
	var initial_snapshot: Dictionary = game_manager.world_runtime_registry.current_snapshot()
	var initial_spawner_states: Array = initial_snapshot.get("enemy_runtime_payload", {}).get("spawner_states", [])
	if initial_spawner_states.is_empty():
		_record_failure("Spawner regression level did not expose any spawner runtime state: %s" % level.level_id)
		await _cleanup_scene(main)
		return

	var initial_turns_until_spawn := int(initial_spawner_states[0].get("turns_until_spawn", -1))
	var first_action := "skip"
	var solution_actions: Array[String] = game_manager.board_state.solution_actions
	if not solution_actions.is_empty():
		first_action = solution_actions[0]
	await game_manager._resolve_player_action(first_action, false)

	var progressed_snapshot: Dictionary = game_manager.world_runtime_registry.current_snapshot()
	var progressed_spawner_states: Array = progressed_snapshot.get("enemy_runtime_payload", {}).get("spawner_states", [])
	_expect(not progressed_spawner_states.is_empty(), "Spawner runtime state should still exist after one action.")
	if not progressed_spawner_states.is_empty():
		var progressed_turns_until_spawn := int(progressed_spawner_states[0].get("turns_until_spawn", -1))
		_expect(
			progressed_turns_until_spawn == initial_turns_until_spawn - 1,
			"Spawner countdown should advance by one after a consumed action."
		)

	game_manager.handle_global_action("undo")
	await get_tree().process_frame
	var undo_snapshot: Dictionary = game_manager.world_runtime_registry.current_snapshot()
	_expect(undo_snapshot.get("enemy_runtime_payload") == initial_snapshot.get("enemy_runtime_payload"), "Undo should restore the initial spawner runtime payload.")

	await game_manager._resolve_player_action(first_action, false)
	game_manager.handle_global_action("reset")
	await get_tree().process_frame
	var reset_snapshot: Dictionary = game_manager.world_runtime_registry.current_snapshot()
	_expect(reset_snapshot.get("enemy_runtime_payload") == initial_snapshot.get("enemy_runtime_payload"), "Reset should restore the initial spawner runtime payload.")

	await _cleanup_scene(main)


func _instantiate_level(world, level):
	var main = MainScene.instantiate()
	main.configure_selected_level(world, level)
	get_tree().root.add_child(main)
	await get_tree().process_frame
	await get_tree().process_frame
	return main


func _cleanup_scene(main) -> void:
	if main == null:
		return
	main.queue_free()
	await get_tree().process_frame


func _find_level(levels: Array, level_id: String):
	for level in levels:
		if level != null and String(level.level_id) == level_id:
			return level
	return null


func _wait_for_replay_completion(game_manager, timeout_seconds: float) -> bool:
	var deadline := Time.get_ticks_msec() + int(timeout_seconds * 1000.0)
	while Time.get_ticks_msec() < deadline:
		if not game_manager.replaying_solution and not game_manager.input_locked:
			return true
		await get_tree().create_timer(0.05).timeout
	return false


func _expect(condition: bool, message: String) -> void:
	if not condition:
		_record_failure(message)


func _record_failure(message: String) -> void:
	_failures.append(message)


func _finish() -> void:
	if _failures.is_empty():
		print("[Regression] Godot runtime regression checks passed.")
		get_tree().quit(0)
		return

	for failure in _failures:
		push_error("[Regression] %s" % failure)
	get_tree().quit(1)
