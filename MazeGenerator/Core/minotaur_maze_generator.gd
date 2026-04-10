extends RefCounted
class_name MinotaurMazeGenerator

const MazeDataScript = preload("res://MazeGenerator/maze_data.gd")
const SolverScript = preload("res://MazeGenerator/Core/minotaur_solver.gd")

const SMALL_SIZES: Array[Vector2i] = [
	Vector2i(4, 4),
	Vector2i(5, 5),
	Vector2i(3, 5),
	Vector2i(4, 3),
	Vector2i(5, 3),
	Vector2i(5, 4),
]
const MEDIUM_SIZES: Array[Vector2i] = [
	Vector2i(6, 6),
	Vector2i(7, 7),
	Vector2i(7, 5),
]
const LARGE_SIZES: Array[Vector2i] = [
	Vector2i(8, 8),
	Vector2i(9, 9),
	Vector2i(11, 11),
]
const SIZE_BUCKETS := {
	"small": SMALL_SIZES,
	"medium": MEDIUM_SIZES,
	"large": LARGE_SIZES,
}
const DIFFICULTIES: Array[String] = ["easy", "medium", "hard", "max"]

var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _init() -> void:
	_rng.randomize()


func generate_board(config: Dictionary) -> MazeData:
	var started_ms := Time.get_ticks_msec()
	var size_category: String = String(config.get("size_mode", "random"))
	if size_category == "random":
		size_category = ["small", "medium", "large"][_rng.randi_range(0, 2)]

	var difficulty: String = String(config.get("difficulty_mode", "random"))
	if difficulty == "random":
		difficulty = DIFFICULTIES[_rng.randi_range(0, DIFFICULTIES.size() - 1)]

	var board_size: Vector2i = _choose_board_size(size_category)
	var cell_size: int = int(config.get("cell_size", 16))
	var candidate_pool_target: int = int(config.get("candidate_pool_target", 18))
	var generation_attempt_limit: int = int(config.get("generation_attempt_limit", 120))
	print(
		"[Startup] MinotaurMazeGenerator.generate_board begin size=%s difficulty=%s cell=%d pool=%d limit=%d" % [
			size_category,
			difficulty,
			cell_size,
			candidate_pool_target,
			generation_attempt_limit,
		]
	)

	var candidates: Array[Dictionary] = []
	for _attempt in range(generation_attempt_limit):
		var attempt_number := _attempt + 1
		var maze_key: Dictionary = _build_candidate_maze_key(board_size)
		var board := MazeDataScript.new()
		board.configure_from_maze_key(maze_key, cell_size, size_category, difficulty)
		var solve_result: Dictionary = SolverScript.solve_board(board)
		if not solve_result["solvable"]:
			if attempt_number == 1 or attempt_number % 10 == 0:
				print(
					"[Startup] MinotaurMazeGenerator attempt %d/%d unsolved after %d ms" % [
						attempt_number,
						generation_attempt_limit,
						Time.get_ticks_msec() - started_ms,
					]
				)
			continue

		maze_key["solution"] = solve_result["solution"]
		maze_key["sol_length"] = solve_result["solution"].size()
		candidates.append(maze_key)
		print(
			"[Startup] MinotaurMazeGenerator attempt %d/%d solved len=%d candidates=%d elapsed=%d ms" % [
				attempt_number,
				generation_attempt_limit,
				maze_key["sol_length"],
				candidates.size(),
				Time.get_ticks_msec() - started_ms,
			]
		)
		if candidates.size() >= candidate_pool_target:
			break

	if candidates.is_empty():
		print(
			"[Startup] MinotaurMazeGenerator using fallback after %d ms" % (
				Time.get_ticks_msec() - started_ms
			)
		)
		var fallback_key: Dictionary = _build_last_resort_maze_key(board_size, cell_size, size_category, difficulty)
		var fallback_board := MazeDataScript.new()
		fallback_board.configure_from_maze_key(fallback_key, cell_size, size_category, difficulty)
		fallback_board.generation_profile_id = "%s_%s_fallback" % [size_category, difficulty]
		print(
			"[Startup] MinotaurMazeGenerator fallback ready in %d ms" % (
				Time.get_ticks_msec() - started_ms
			)
		)
		return fallback_board

	var selected_maze_key: Dictionary = _select_candidate(candidates, difficulty)
	var final_board := MazeDataScript.new()
	final_board.configure_from_maze_key(selected_maze_key, cell_size, size_category, difficulty)
	final_board.generation_profile_id = "%s_%s_runtime" % [size_category, difficulty]
	print(
		"[Startup] MinotaurMazeGenerator.generate_board end candidates=%d selected_len=%d elapsed=%d ms" % [
			candidates.size(),
			int(selected_maze_key.get("sol_length", 0)),
			Time.get_ticks_msec() - started_ms,
		]
	)
	return final_board


func _choose_board_size(size_category: String) -> Vector2i:
	var sizes: Array[Vector2i] = SIZE_BUCKETS.get(size_category, SMALL_SIZES)
	return sizes[_rng.randi_range(0, sizes.size() - 1)]


func _build_candidate_maze_key(board_size: Vector2i) -> Dictionary:
	var walls: Array = []
	while true:
		walls.clear()
		for edge in _build_all_edges(board_size):
			if _rng.randf() < 0.5:
				walls.append(edge)

		if _is_connected(board_size, walls):
			break

	var player_start := Vector2i.ZERO
	var mino_start := Vector2i.ZERO
	var goal := Vector2i.ZERO
	var token_valid := false
	while not token_valid:
		player_start = _random_cell(board_size)
		mino_start = _random_cell(board_size)
		goal = _random_cell(board_size)
		token_valid = player_start != goal and player_start != mino_start

	return {
		"size_board": [board_size.x, board_size.y],
		"walls": walls.duplicate(true),
		"player_start": [player_start.x, player_start.y],
		"mino_start": [mino_start.x, mino_start.y],
		"goal": [goal.x, goal.y],
	}


func _build_last_resort_maze_key(
	board_size: Vector2i,
	cell_size: int,
	size_category: String,
	difficulty: String
) -> Dictionary:
	for _attempt in range(256):
		var player_start: Vector2i = _random_cell(board_size)
		var mino_start: Vector2i = _random_cell(board_size)
		var goal: Vector2i = _random_cell(board_size)
		if player_start == goal or player_start == mino_start:
			continue
		var maze_key := {
			"size_board": [board_size.x, board_size.y],
			"walls": [],
			"player_start": [player_start.x, player_start.y],
			"mino_start": [mino_start.x, mino_start.y],
			"goal": [goal.x, goal.y],
		}
		var board := MazeDataScript.new()
		board.configure_from_maze_key(maze_key, cell_size, size_category, difficulty)
		var solve_result: Dictionary = SolverScript.solve_board(board)
		if solve_result["solvable"]:
			maze_key["solution"] = solve_result["solution"]
			maze_key["sol_length"] = solve_result["solution"].size()
			return maze_key

	var hardcoded_key := {
		"size_board": [4, 4],
		"walls": [],
		"player_start": [0, 0],
		"mino_start": [1, 1],
		"goal": [3, 3],
	}
	var hardcoded_board := MazeDataScript.new()
	hardcoded_board.configure_from_maze_key(hardcoded_key, cell_size, size_category, difficulty)
	var hardcoded_solution: Dictionary = SolverScript.solve_board(hardcoded_board)
	hardcoded_key["solution"] = hardcoded_solution.get("solution", [])
	hardcoded_key["sol_length"] = hardcoded_key["solution"].size()
	return hardcoded_key


func _select_candidate(candidates: Array[Dictionary], difficulty: String) -> Dictionary:
	candidates.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return int(a.get("sol_length", 0)) < int(b.get("sol_length", 0))
	)

	if difficulty == "max":
		return candidates.back()
	if difficulty == "random":
		return candidates[_rng.randi_range(0, candidates.size() - 1)]

	var bucket_size: int = max(1, int(ceil(float(candidates.size()) / 3.0)))
	var start_index := 0
	var end_index := candidates.size()

	match difficulty:
		"easy":
			start_index = 0
			end_index = min(bucket_size, candidates.size())
		"medium":
			start_index = min(bucket_size, candidates.size() - 1)
			end_index = min(bucket_size * 2, candidates.size())
		"hard":
			start_index = min(bucket_size * 2, candidates.size() - 1)
			end_index = candidates.size()
		_:
			return candidates[_rng.randi_range(0, candidates.size() - 1)]

	var filtered: Array[Dictionary] = []
	for index in range(start_index, end_index):
		filtered.append(candidates[index])

	if filtered.is_empty():
		return candidates.back()

	return filtered[_rng.randi_range(0, filtered.size() - 1)]


func _build_all_edges(board_size: Vector2i) -> Array:
	var edges: Array = []
	for y in range(board_size.y):
		for x in range(board_size.x):
			if x + 1 < board_size.x:
				edges.append([[x, y], [x + 1, y]])
			if y + 1 < board_size.y:
				edges.append([[x, y], [x, y + 1]])
	return edges


func _is_connected(board_size: Vector2i, walls: Array) -> bool:
	var wall_lookup: Dictionary = {}
	for wall in walls:
		wall_lookup[_edge_key(Vector2i(wall[0][0], wall[0][1]), Vector2i(wall[1][0], wall[1][1]))] = true

	var start := Vector2i.ZERO
	var queue: Array[Vector2i] = [start]
	var visited: Dictionary = {start: true}
	var directions := [Vector2i.LEFT, Vector2i.RIGHT, Vector2i.UP, Vector2i.DOWN]

	while not queue.is_empty():
		var current: Vector2i = queue.pop_front()
		for direction in directions:
			var next_cell: Vector2i = current + direction
			if next_cell.x < 0 or next_cell.y < 0 or next_cell.x >= board_size.x or next_cell.y >= board_size.y:
				continue
			if wall_lookup.has(_edge_key(current, next_cell)):
				continue
			if visited.has(next_cell):
				continue
			visited[next_cell] = true
			queue.append(next_cell)

	return visited.size() == board_size.x * board_size.y


func _edge_key(a: Vector2i, b: Vector2i) -> String:
	if a.x > b.x or (a.x == b.x and a.y > b.y):
		return "%d,%d|%d,%d" % [b.x, b.y, a.x, a.y]
	return "%d,%d|%d,%d" % [a.x, a.y, b.x, b.y]


func _random_cell(board_size: Vector2i) -> Vector2i:
	return Vector2i(
		_rng.randi_range(0, board_size.x - 1),
		_rng.randi_range(0, board_size.y - 1)
	)
