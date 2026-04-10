extends Node

signal floor_generated(board_state)

const MinotaurMazeGeneratorScript = preload("res://MazeGenerator/Core/minotaur_maze_generator.gd")
const MazeDataScript = preload("res://MazeGenerator/maze_data.gd")

@export_enum("small", "medium", "large", "random") var board_size_mode: String = "random"
@export_enum("easy", "medium", "hard", "max", "random") var difficulty_mode: String = "max"
@export var cell_size: int = 16
@export var candidate_pool_target: int = 18
@export var generation_attempt_limit: int = 120
@export var use_saved_resource_cycle: bool = true
@export_dir var saved_resource_directory: String = "res://Resources"

var _generator
var _saved_resource_paths: Array[String] = []
var _saved_resource_index: int = 0


func _ready() -> void:
	_generator = MinotaurMazeGeneratorScript.new()
	_refresh_saved_resource_paths()
	print("[Startup] MazeGenerator._ready generator initialized")


func generate_floor(_floor_index: int = 1) -> MazeData:
	if use_saved_resource_cycle:
		var saved_board := _load_next_saved_board()
		if saved_board != null:
			floor_generated.emit(saved_board)
			return saved_board

	print(
		"[Startup] MazeGenerator.generate_floor begin size=%s difficulty=%s pool=%d limit=%d" % [
			board_size_mode,
			difficulty_mode,
			candidate_pool_target,
			generation_attempt_limit,
		]
	)
	var started_ms := Time.get_ticks_msec()
	var board_state: MazeData = _generator.generate_board({
		"size_mode": board_size_mode,
		"difficulty_mode": difficulty_mode,
		"cell_size": cell_size,
		"candidate_pool_target": candidate_pool_target,
		"generation_attempt_limit": generation_attempt_limit,
	})
	print(
		"[Startup] MazeGenerator.generate_floor end in %d ms" % (
			Time.get_ticks_msec() - started_ms
		)
	)
	floor_generated.emit(board_state)
	return board_state


func _refresh_saved_resource_paths() -> void:
	_saved_resource_paths.clear()
	if saved_resource_directory.is_empty():
		return

	var directory := DirAccess.open(saved_resource_directory)
	if directory == null:
		push_warning("[Startup] MazeGenerator could not open saved maze directory: %s" % saved_resource_directory)
		return

	directory.list_dir_begin()
	while true:
		var entry := directory.get_next()
		if entry.is_empty():
			break
		if directory.current_is_dir():
			continue
		if not entry.ends_with(".tres"):
			continue
		if not entry.begins_with("minotaur_"):
			continue
		_saved_resource_paths.append(saved_resource_directory.path_join(entry))
	directory.list_dir_end()

	_saved_resource_paths.sort()
	print("[Startup] MazeGenerator found %d saved maze resources in %s" % [_saved_resource_paths.size(), saved_resource_directory])


func _load_next_saved_board() -> MazeData:
	if _saved_resource_paths.is_empty():
		return null

	if _saved_resource_index >= _saved_resource_paths.size():
		_saved_resource_index = 0

	var resource_path := _saved_resource_paths[_saved_resource_index]
	_saved_resource_index += 1

	var saved_resource := load(resource_path)
	var board_state: MazeData = MazeDataScript.from_saved_resource(saved_resource)
	if board_state == null:
		push_warning("[Startup] MazeGenerator could not load maze resource: %s" % resource_path)
		return null

	board_state.cell_size = cell_size
	board_state.generation_mode = "RESOURCE_CYCLE"
	print(
		"[Startup] MazeGenerator loaded saved maze %s (%d/%d)" % [
			resource_path,
			_saved_resource_index,
			_saved_resource_paths.size(),
		]
	)
	return board_state
