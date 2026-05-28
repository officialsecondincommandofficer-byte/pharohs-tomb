extends Node

signal floor_generated(board_state)

const MinotaurMazeGeneratorScript = preload("res://MazeGenerator/Core/minotaur_maze_generator.gd")

@export_enum("small", "medium", "large", "random") var board_size_mode: String = "random"
@export_enum("easy", "medium", "hard", "max", "random") var difficulty_mode: String = "max"
@export var cell_size: int = 16
@export var candidate_pool_target: int = 18
@export var generation_attempt_limit: int = 120

var _generator


func _ready() -> void:
	_generator = MinotaurMazeGeneratorScript.new()
	print("[Startup] MazeGenerator._ready generator initialized")


func generate_floor(_floor_index: int = 1) -> MazeData:
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
