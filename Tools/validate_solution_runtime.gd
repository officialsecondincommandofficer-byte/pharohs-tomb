extends SceneTree

const EnemyManagerScene := preload("res://EnemyManager/EnemyManager.tscn")
const DEFAULT_RESOURCE_CANDIDATES := [
	"res://Resources/Worlds/SolverTestMazes/minotaur_20260531_053515_12x12_len031_max_001.tres",
	"res://Resources/Test/minotaur_20260531_053515_12x12_len031_max_001.tres",
	"res://Resources/Worlds/SolverTestMazes/minotaur_20260531_051308_12x12_len036_max_001.tres",
	"res://Resources/Test/minotaur_20260531_051308_12x12_len036_max_001.tres",
]


func _initialize() -> void:
	_run_validation.call_deferred()


func _run_validation() -> void:
	var resource_path := _resolve_resource_path()
	if resource_path.is_empty():
		print("RUNTIME_FAIL missing_resource candidates=%s" % [DEFAULT_RESOURCE_CANDIDATES])
		quit(1)
		return

	var saved_resource := load(resource_path)
	if saved_resource == null:
		print("RUNTIME_FAIL unloadable_resource path=%s" % [resource_path])
		quit(1)
		return

	var board := MazeData.from_saved_resource(saved_resource)
	if board == null:
		print("RUNTIME_FAIL invalid_board_resource path=%s" % [resource_path])
		quit(1)
		return

	var enemy_manager = EnemyManagerScene.instantiate()
	root.add_child(enemy_manager)
	enemy_manager.setup_floor(board)

	var player_cell: Vector2i = board.player_spawn
	var turn_index := 0
	for action in board.solution_actions:
		turn_index += 1
		var transition: Dictionary = board.resolve_player_transition(player_cell, action)
		var stepped_player: Vector2i = transition.get("stepped_cell", player_cell)
		var next_player: Vector2i = transition.get("resolved_cell", player_cell)

		if board.is_trap_cell(stepped_player):
			print("RUNTIME_FAIL trap_on_step turn=%d action=%s cell=%s" % [turn_index, action, stepped_player])
			quit(1)
			return

		var enemy_results: Array = await enemy_manager.begin_enemy_phase(stepped_player)
		var enemy_contacted_player := false
		for enemy_result in enemy_results:
			if bool(enemy_result.get("contact_player", false)):
				enemy_contacted_player = true
				print("RUNTIME_FAIL enemy_contact turn=%d action=%s result=%s" % [turn_index, action, enemy_result])
				break
		if enemy_contacted_player or enemy_manager.any_enemy_at_cell(stepped_player):
			print("RUNTIME_FAIL enemy_occupies_step turn=%d action=%s player=%s enemies=%s" % [
				turn_index,
				action,
				stepped_player,
				enemy_manager.get_current_cells(),
			])
			quit(1)
			return

		var turn_end_transition: Dictionary = board.resolve_player_turn_end_transition(next_player)
		player_cell = turn_end_transition.get("resolved_cell", next_player)
		if board.is_trap_cell(player_cell):
			print("RUNTIME_FAIL trap_on_turn_end turn=%d action=%s cell=%s" % [turn_index, action, player_cell])
			quit(1)
			return
		if board.is_exit_cell(player_cell):
			print("RUNTIME_OK win turn=%d action=%s cell=%s" % [turn_index, action, player_cell])
			quit(0)
			return

	print("RUNTIME_DONE no_win final_player=%s" % [player_cell])
	quit(1)


func _resolve_resource_path() -> String:
	for candidate in DEFAULT_RESOURCE_CANDIDATES:
		if ResourceLoader.exists(candidate):
			return candidate
	return ""
