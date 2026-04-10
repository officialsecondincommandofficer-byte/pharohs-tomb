extends RefCounted
class_name MazeData

const SAVE_VERSION := 1

const ACTION_TO_DIRECTION := {
	"left": Vector2i.LEFT,
	"right": Vector2i.RIGHT,
	"up": Vector2i.UP,
	"down": Vector2i.DOWN,
}

var width: int = 0
var height: int = 0
var cell_size: int = 16
var wall_density: float = 0.0
var size_category: String = "small"
var difficulty_category: String = "easy"
var floor_cells: Array[Vector2i] = []
var wall_cells: Array[Vector2i] = []
var horizontal_walls: Array[Vector2i] = []
var vertical_walls: Array[Vector2i] = []
var player_spawn: Vector2i = Vector2i.ZERO
var minotaur_spawn: Vector2i = Vector2i.ZERO
var exit_cell: Vector2i = Vector2i.ZERO
var solution_actions: Array[String] = []
var solution_total_steps: int = 0
var maze_key: Dictionary = {}
var generation_mode: String = "RUNTIME_GENERATED"
var generation_profile_id: String = ""
var display_name: String = ""
var saved_at_unix: int = 0

var _floor_lookup: Dictionary = {}
var _horizontal_wall_lookup: Dictionary = {}
var _vertical_wall_lookup: Dictionary = {}


func configure_from_maze_key(
	next_maze_key: Dictionary,
	next_cell_size: int,
	next_size_category: String,
	next_difficulty_category: String
) -> void:
	width = int(_coerce_vector2i(next_maze_key.get("size_board", Vector2i.ONE)).x)
	height = int(_coerce_vector2i(next_maze_key.get("size_board", Vector2i.ONE)).y)
	cell_size = next_cell_size
	size_category = next_size_category
	difficulty_category = next_difficulty_category
	maze_key = next_maze_key.duplicate(true)
	floor_cells.clear()
	wall_cells.clear()
	horizontal_walls.clear()
	vertical_walls.clear()
	solution_actions.clear()
	_floor_lookup.clear()
	_horizontal_wall_lookup.clear()
	_vertical_wall_lookup.clear()

	for y in range(height):
		for x in range(width):
			add_floor_cell(Vector2i(x, y))

	for raw_wall in next_maze_key.get("walls", []):
		_add_wall_from_edge(raw_wall)

	player_spawn = _coerce_vector2i(next_maze_key.get("player_start", Vector2i.ZERO))
	minotaur_spawn = _coerce_vector2i(next_maze_key.get("mino_start", Vector2i.ZERO))
	exit_cell = _coerce_vector2i(next_maze_key.get("goal", Vector2i.ZERO))

	for action in next_maze_key.get("solution", []):
		solution_actions.append(String(action))

	solution_total_steps = int(next_maze_key.get("sol_length", solution_actions.size()))
	wall_density = float(horizontal_walls.size() + vertical_walls.size()) / max(float(_edge_count()), 1.0)


func to_world(cell: Vector2i) -> Vector2:
	return Vector2(
		cell.x * cell_size + cell_size / 2.0,
		cell.y * cell_size + cell_size / 2.0
	)


func to_map(world_position: Vector2) -> Vector2i:
	return Vector2i(
		int(floor(world_position.x / cell_size)),
		int(floor(world_position.y / cell_size))
	)


func is_in_bounds(cell: Vector2i) -> bool:
	return cell.x >= 0 and cell.y >= 0 and cell.x < width and cell.y < height


func is_walkable(cell: Vector2i) -> bool:
	return _floor_lookup.has(cell)


func add_floor_cell(cell: Vector2i) -> void:
	if _floor_lookup.has(cell):
		return
	floor_cells.append(cell)
	_floor_lookup[cell] = true


func add_horizontal_wall(edge: Vector2i) -> void:
	if _horizontal_wall_lookup.has(edge):
		return
	horizontal_walls.append(edge)
	_horizontal_wall_lookup[edge] = true


func add_vertical_wall(edge: Vector2i) -> void:
	if _vertical_wall_lookup.has(edge):
		return
	vertical_walls.append(edge)
	_vertical_wall_lookup[edge] = true


func has_horizontal_wall(edge: Vector2i) -> bool:
	return _horizontal_wall_lookup.has(edge)


func has_vertical_wall(edge: Vector2i) -> bool:
	return _vertical_wall_lookup.has(edge)


func has_wall_between(a: Vector2i, b: Vector2i) -> bool:
	var delta := b - a
	if abs(delta.x) + abs(delta.y) != 1:
		return true

	if delta.x != 0:
		return has_vertical_wall(Vector2i(max(a.x, b.x), a.y))

	return has_horizontal_wall(Vector2i(a.x, max(a.y, b.y)))


func can_step(a: Vector2i, b: Vector2i) -> bool:
	if not is_in_bounds(a) or not is_in_bounds(b):
		return false
	return not has_wall_between(a, b)


func get_cardinal_neighbors(cell: Vector2i) -> Array[Vector2i]:
	var neighbors: Array[Vector2i] = []
	for direction in ACTION_TO_DIRECTION.values():
		var next_cell: Vector2i = cell + direction
		if can_step(cell, next_cell):
			neighbors.append(next_cell)
	return neighbors


func get_move_options(cell: Vector2i, include_skip: bool = true) -> Array[String]:
	var options: Array[String] = []
	if include_skip:
		options.append("skip")

	for action in ["right", "left", "up", "down"]:
		var next_cell: Vector2i = apply_action(cell, action)
		if next_cell != cell:
			options.append(action)

	return options


func apply_action(cell: Vector2i, action: String) -> Vector2i:
	if action == "skip":
		return cell

	if not ACTION_TO_DIRECTION.has(action):
		return cell

	var next_cell: Vector2i = cell + ACTION_TO_DIRECTION[action]
	if not can_step(cell, next_cell):
		return cell

	return next_cell


func build_floor_lookup() -> Dictionary:
	return _floor_lookup.duplicate()


func to_saved_payload(display_name: String = "", saved_at_unix: int = 0) -> Dictionary:
	return {
		"version": SAVE_VERSION,
		"display_name": display_name,
		"saved_at_unix": saved_at_unix,
		"width": width,
		"height": height,
		"cell_size": cell_size,
		"size_category": size_category,
		"difficulty_category": difficulty_category,
		"horizontal_walls": horizontal_walls.duplicate(),
		"vertical_walls": vertical_walls.duplicate(),
		"player_spawn": player_spawn,
		"minotaur_spawn": minotaur_spawn,
		"exit_cell": exit_cell,
		"solution_actions": solution_actions.duplicate(),
		"solution_total_steps": solution_total_steps,
		"generation_mode": generation_mode,
		"generation_profile_id": generation_profile_id,
	}


static func from_saved_payload(payload: Dictionary) -> MazeData:
	var board := MazeData.new()
	board.width = int(payload.get("width", 0))
	board.height = int(payload.get("height", 0))
	board.cell_size = int(payload.get("cell_size", 16))
	board.size_category = String(payload.get("size_category", "small"))
	board.difficulty_category = String(payload.get("difficulty_category", "easy"))
	board.display_name = String(payload.get("display_name", ""))
	board.saved_at_unix = int(payload.get("saved_at_unix", 0))
	board.player_spawn = board._coerce_vector2i(payload.get("player_spawn", Vector2i.ZERO))
	board.minotaur_spawn = board._coerce_vector2i(payload.get("minotaur_spawn", Vector2i.ZERO))
	board.exit_cell = board._coerce_vector2i(payload.get("exit_cell", Vector2i.ZERO))
	board.generation_mode = String(payload.get("generation_mode", "RUNTIME_GENERATED"))
	board.generation_profile_id = String(payload.get("generation_profile_id", ""))
	board.solution_total_steps = int(payload.get("solution_total_steps", 0))

	for y in range(board.height):
		for x in range(board.width):
			board.add_floor_cell(Vector2i(x, y))

	for horizontal_wall in payload.get("horizontal_walls", []):
		board.add_horizontal_wall(board._coerce_vector2i(horizontal_wall))

	for vertical_wall in payload.get("vertical_walls", []):
		board.add_vertical_wall(board._coerce_vector2i(vertical_wall))

	for action in payload.get("solution_actions", []):
		board.solution_actions.append(String(action))

	if board.solution_total_steps <= 0:
		board.solution_total_steps = board.solution_actions.size()

	board.wall_density = float(board.horizontal_walls.size() + board.vertical_walls.size()) / max(float(board._edge_count()), 1.0)
	board.maze_key = board._build_maze_key_from_state()
	return board


static func from_saved_resource(saved_resource: Resource) -> MazeData:
	if saved_resource == null:
		return null
	if saved_resource.has_method("to_payload"):
		return from_saved_payload(saved_resource.to_payload())
	return null


func _add_wall_from_edge(raw_wall) -> void:
	var nodes: Array = raw_wall
	if nodes.size() != 2:
		return

	var a: Vector2i = _coerce_vector2i(nodes[0])
	var b: Vector2i = _coerce_vector2i(nodes[1])
	var delta := b - a
	if abs(delta.x) + abs(delta.y) != 1:
		return

	if delta.x != 0:
		add_vertical_wall(Vector2i(max(a.x, b.x), a.y))
	else:
		add_horizontal_wall(Vector2i(a.x, max(a.y, b.y)))


func _build_maze_key_from_state() -> Dictionary:
	var serialized_walls: Array = []

	for edge in horizontal_walls:
		serialized_walls.append([
			[edge.x, edge.y - 1],
			[edge.x, edge.y],
		])

	for edge in vertical_walls:
		serialized_walls.append([
			[edge.x - 1, edge.y],
			[edge.x, edge.y],
		])

	return {
		"size_board": [width, height],
		"walls": serialized_walls,
		"player_start": [player_spawn.x, player_spawn.y],
		"mino_start": [minotaur_spawn.x, minotaur_spawn.y],
		"goal": [exit_cell.x, exit_cell.y],
		"solution": solution_actions.duplicate(),
		"sol_length": solution_total_steps,
	}


func _edge_count() -> int:
	return width * max(height - 1, 0) + max(width - 1, 0) * height


func _coerce_vector2i(raw_value) -> Vector2i:
	if raw_value is Vector2i:
		return raw_value
	if raw_value is Vector2:
		return Vector2i(int(raw_value.x), int(raw_value.y))
	if raw_value is Array and raw_value.size() >= 2:
		return Vector2i(int(raw_value[0]), int(raw_value[1]))
	return Vector2i.ZERO
