extends Node

signal floor_generated(board_state)

const MazeDataScript = preload("res://MazeGenerator/maze_data.gd")

@export var base_width: int = 25
@export var base_height: int = 19
@export var floor_size_presets: Array[Vector2i] = [
	Vector2i(8, 8),
	Vector2i(10, 10),
	Vector2i(16, 16),
]
@export var cell_size: int = 16
@export var base_turn_limit: int = 90
@export var base_visibility_radius: int = 4
@export var interior_wall_density_presets: Array[float] = [0.33, 0.4, 0.5]
@export var min_wall_segment_length: int = 2
@export var max_wall_segment_length: int = 5
@export var max_wall_placement_attempts: int = 256
@export var spawn_clear_radius: int = 0
@export_range(0.0, 0.5, 0.01) var perimeter_attachment_chance: float = 0.1
@export var max_perimeter_attachment_length: int = 2

var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.randomize()


func generate_floor(floor_index: int = 1):
	var chosen_size: Vector2i = _choose_floor_size()
	var chosen_wall_density: float = _choose_wall_density()
	var width: int = chosen_size.x
	var height: int = chosen_size.y
	var start := Vector2i(1, 1)
	var board_state: MazeData = MazeDataScript.new()

	board_state.floor_index = floor_index
	board_state.width = width
	board_state.height = height
	board_state.cell_size = cell_size
	board_state.wall_density = chosen_wall_density
	board_state.base_visibility_radius = max(3, base_visibility_radius - (floor_index - 1))
	board_state.player_spawn = start

	_populate_floor_cells(board_state)
	_add_perimeter_walls(board_state)
	_place_sparse_wall_segments(board_state, start, width, height, chosen_wall_density)

	board_state.exit_cell = _find_farthest_cell(start, board_state)
	var critical_path: Array[Vector2i] = _find_path(start, board_state.exit_cell, board_state)
	board_state.key_cell = critical_path[max(1, critical_path.size() / 2)]

	var reserved: Dictionary = {
		board_state.player_spawn: true,
		board_state.exit_cell: true,
		board_state.key_cell: true,
	}

	board_state.enemy_spawns = _build_enemy_spawns(board_state, reserved)
	for enemy_spawn in board_state.enemy_spawns:
		reserved[enemy_spawn["cell"]] = true

	board_state.item_spawns = _build_item_spawns(board_state, reserved)
	board_state.turn_limit = max(
		base_turn_limit,
		critical_path.size() * 4 + board_state.item_spawns.size() * 3
	)

	floor_generated.emit(board_state)
	return board_state


func _make_odd(value: int) -> int:
	return value if value % 2 == 1 else value + 1


func _choose_floor_size() -> Vector2i:
	var size_options: Array[Vector2i] = floor_size_presets.duplicate()
	size_options.append(Vector2i(base_width, base_height))
	return size_options[_rng.randi_range(0, size_options.size() - 1)]


func _choose_wall_density() -> float:
	return interior_wall_density_presets[_rng.randi_range(0, interior_wall_density_presets.size() - 1)]


func _populate_floor_cells(board_state: MazeData) -> void:
	for y in board_state.height:
		for x in board_state.width:
			board_state.add_floor_cell(Vector2i(x, y))


func _add_perimeter_walls(board_state: MazeData) -> void:
	for x in board_state.width:
		board_state.add_horizontal_wall(Vector2i(x, 0))
		board_state.add_horizontal_wall(Vector2i(x, board_state.height))

	for y in board_state.height:
		board_state.add_vertical_wall(Vector2i(0, y))
		board_state.add_vertical_wall(Vector2i(board_state.width, y))


func _place_sparse_wall_segments(
	board_state: MazeData,
	start: Vector2i,
	width: int,
	height: int,
	wall_density: float
) -> void:
	var interior_area: int = max(width - 2, 0) * max(height - 2, 0)
	var target_wall_edges: int = int(round(float(interior_area) * wall_density))
	var placed_wall_edges := 0
	var attempts := 0

	while placed_wall_edges < target_wall_edges and attempts < max_wall_placement_attempts:
		attempts += 1
		var horizontal: bool = _rng.randf() < 0.5
		var attach_to_perimeter: bool = _rng.randf() < perimeter_attachment_chance
		var segment_edges: Array[Vector2i] = _build_candidate_segment(
			width,
			height,
			horizontal,
			attach_to_perimeter
		)
		if segment_edges.is_empty():
			continue
		if not _can_place_wall_segment(
			board_state,
			segment_edges,
			horizontal,
			attach_to_perimeter,
			start,
			width,
			height
		):
			continue

		_apply_wall_segment(board_state, segment_edges, horizontal, true)
		if not _all_floor_cells_reachable(board_state, start):
			_apply_wall_segment(board_state, segment_edges, horizontal, false)
			continue

		placed_wall_edges += segment_edges.size()


func _build_candidate_segment(
	width: int,
	height: int,
	horizontal: bool,
	attach_to_perimeter: bool
) -> Array[Vector2i]:
	var edges: Array[Vector2i] = []

	if horizontal:
		var available_length_x := width - 2
		if available_length_x < min_wall_segment_length:
			return edges

		var length_cap: int = max_perimeter_attachment_length if attach_to_perimeter else max_wall_segment_length
		var max_length: int = min(length_cap, available_length_x)
		var length: int = _rng.randi_range(min_wall_segment_length, max_length)
		var start_x: int
		var y: int
		if attach_to_perimeter:
			y = _rng.randi_range(1, height - 1)
			start_x = 0 if _rng.randf() < 0.5 else width - length
		else:
			var max_start_x := width - length - 1
			if max_start_x < 1:
				return edges
			start_x = _rng.randi_range(1, max_start_x)
			y = _rng.randi_range(2, height - 2)
		for index in length:
			edges.append(Vector2i(start_x + index, y))
	else:
		var available_length_y := height - 2
		if available_length_y < min_wall_segment_length:
			return edges

		var vertical_length_cap: int = max_perimeter_attachment_length if attach_to_perimeter else max_wall_segment_length
		var max_length_vertical: int = min(vertical_length_cap, available_length_y)
		var vertical_length: int = _rng.randi_range(min_wall_segment_length, max_length_vertical)
		var x: int
		var start_y: int
		if attach_to_perimeter:
			x = _rng.randi_range(1, width - 1)
			start_y = 0 if _rng.randf() < 0.5 else height - vertical_length
		else:
			var max_start_y := height - vertical_length - 1
			if max_start_y < 1:
				return edges
			x = _rng.randi_range(2, width - 2)
			start_y = _rng.randi_range(1, max_start_y)
		for index in vertical_length:
			edges.append(Vector2i(x, start_y + index))

	return edges


func _can_place_wall_segment(
	board_state: MazeData,
	segment_edges: Array[Vector2i],
	horizontal: bool,
	attach_to_perimeter: bool,
	start: Vector2i,
	width: int,
	height: int
) -> bool:
	for edge in segment_edges:
		if _edge_exists(board_state, edge, horizontal):
			return false
		if _edge_touches_spawn(edge, horizontal, start, width, height):
			return false
		if _has_parallel_neighbor(board_state, edge, horizontal, attach_to_perimeter, width, height):
			return false

	return true


func _apply_wall_segment(
	board_state: MazeData,
	segment_edges: Array[Vector2i],
	horizontal: bool,
	add_segment: bool
) -> void:
	for edge in segment_edges:
		if horizontal:
			if add_segment:
				board_state.add_horizontal_wall(edge)
			else:
				board_state.remove_horizontal_wall(edge)
		else:
			if add_segment:
				board_state.add_vertical_wall(edge)
			else:
				board_state.remove_vertical_wall(edge)


func _edge_exists(board_state: MazeData, edge: Vector2i, horizontal: bool) -> bool:
	if horizontal:
		return board_state.has_horizontal_wall(edge)
	return board_state.has_vertical_wall(edge)


func _edge_touches_spawn(
	edge: Vector2i,
	horizontal: bool,
	start: Vector2i,
	width: int,
	height: int
) -> bool:
	var adjacent_cells: Array[Vector2i] = _adjacent_cells_for_edge(edge, horizontal, width, height)
	for cell in adjacent_cells:
		if cell.distance_to(start) <= float(spawn_clear_radius) + 0.5:
			return true
	return false


func _adjacent_cells_for_edge(
	edge: Vector2i,
	horizontal: bool,
	width: int,
	height: int
) -> Array[Vector2i]:
	var cells: Array[Vector2i] = []
	if horizontal:
		var upper := Vector2i(edge.x, edge.y - 1)
		var lower := Vector2i(edge.x, edge.y)
		if _cell_in_bounds(upper, width, height):
			cells.append(upper)
		if _cell_in_bounds(lower, width, height):
			cells.append(lower)
	else:
		var left := Vector2i(edge.x - 1, edge.y)
		var right := Vector2i(edge.x, edge.y)
		if _cell_in_bounds(left, width, height):
			cells.append(left)
		if _cell_in_bounds(right, width, height):
			cells.append(right)
	return cells


func _cell_in_bounds(cell: Vector2i, width: int, height: int) -> bool:
	return cell.x >= 0 and cell.y >= 0 and cell.x < width and cell.y < height


func _has_parallel_neighbor(
	board_state: MazeData,
	edge: Vector2i,
	horizontal: bool,
	attach_to_perimeter: bool,
	width: int,
	height: int
) -> bool:
	if horizontal:
		var upper_edge := Vector2i(edge.x, edge.y - 1)
		var lower_edge := Vector2i(edge.x, edge.y + 1)
		var has_upper_parallel := board_state.has_horizontal_wall(upper_edge)
		var has_lower_parallel := board_state.has_horizontal_wall(lower_edge)

		if attach_to_perimeter and edge.y == 1:
			has_upper_parallel = false
		elif attach_to_perimeter and edge.y == height - 1:
			has_lower_parallel = false

		return has_upper_parallel or has_lower_parallel

	var left_edge := Vector2i(edge.x - 1, edge.y)
	var right_edge := Vector2i(edge.x + 1, edge.y)
	var has_left_parallel := board_state.has_vertical_wall(left_edge)
	var has_right_parallel := board_state.has_vertical_wall(right_edge)

	if attach_to_perimeter and edge.x == 1:
		has_left_parallel = false
	elif attach_to_perimeter and edge.x == width - 1:
		has_right_parallel = false

	return has_left_parallel or has_right_parallel


func _all_floor_cells_reachable(board_state: MazeData, start: Vector2i) -> bool:
	var total_floor_cells := board_state.floor_cells.size()
	var queue: Array[Vector2i] = [start]
	var visited: Dictionary = {start: true}

	while not queue.is_empty():
		var current: Vector2i = queue.pop_front()
		for neighbor in board_state.get_cardinal_neighbors(current):
			if visited.has(neighbor):
				continue
			visited[neighbor] = true
			queue.append(neighbor)

	return visited.size() == total_floor_cells


func _find_farthest_cell(start: Vector2i, board_state: MazeData) -> Vector2i:
	var queue: Array[Vector2i] = [start]
	var visited: Dictionary = {start: true}
	var farthest: Vector2i = start

	while not queue.is_empty():
		var current: Vector2i = queue.pop_front()
		farthest = current

		for neighbor in board_state.get_cardinal_neighbors(current):
			if visited.has(neighbor):
				continue
			visited[neighbor] = true
			queue.append(neighbor)

	return farthest


func _find_path(start: Vector2i, goal: Vector2i, board_state: MazeData) -> Array[Vector2i]:
	var queue: Array[Vector2i] = [start]
	var came_from: Dictionary = {start: start}

	while not queue.is_empty():
		var current: Vector2i = queue.pop_front()
		if current == goal:
			break

		for neighbor in board_state.get_cardinal_neighbors(current):
			if came_from.has(neighbor):
				continue
			came_from[neighbor] = current
			queue.append(neighbor)

	if not came_from.has(goal):
		return [start]

	var path: Array[Vector2i] = [goal]
	var cursor := goal
	while cursor != start:
		cursor = came_from[cursor]
		path.push_front(cursor)
	return path


func _build_enemy_spawns(board_state: MazeData, reserved: Dictionary) -> Array[Dictionary]:
	var ordered_cells := _cells_by_distance(board_state.player_spawn, board_state)
	var enemy_spawns: Array[Dictionary] = []

	for cell in ordered_cells:
		if reserved.has(cell):
			continue
		if cell.distance_to(board_state.player_spawn) < 7.0:
			continue
		if cell.distance_to(board_state.exit_cell) < 4.0:
			continue

		enemy_spawns.append({
			"type": "chaser",
			"cell": cell,
		})
		reserved[cell] = true
		break

	for cell in ordered_cells:
		if reserved.has(cell):
			continue
		if cell.distance_to(board_state.player_spawn) < 6.0:
			continue
		if cell.distance_to(board_state.exit_cell) < 4.0:
			continue

		enemy_spawns.append({
			"type": "chaser_vertical",
			"cell": cell,
			"move_priority": "vertical",
			"tint": Color(0.82, 0.12, 0.08, 1.0),
		})
		reserved[cell] = true
		break

	return enemy_spawns


func _cells_by_distance(origin: Vector2i, board_state: MazeData) -> Array[Vector2i]:
	var queue: Array[Vector2i] = [origin]
	var visited: Dictionary = {origin: true}
	var ordered: Array[Vector2i] = []

	while not queue.is_empty():
		var current: Vector2i = queue.pop_front()
		ordered.push_front(current)

		for neighbor in board_state.get_cardinal_neighbors(current):
			if visited.has(neighbor):
				continue
			visited[neighbor] = true
			queue.append(neighbor)

	return ordered


func _build_patrol_route(start: Vector2i, board_state: MazeData) -> Array[Vector2i]:
	var route: Array[Vector2i] = [start]
	var current := start
	var previous := Vector2i(-999, -999)

	for _step in 3:
		var options: Array[Vector2i] = []
		for neighbor in board_state.get_cardinal_neighbors(current):
			if neighbor == previous:
				continue
			options.append(neighbor)

		if options.is_empty():
			break

		var next: Vector2i = options[_rng.randi_range(0, options.size() - 1)]
		route.append(next)
		previous = current
		current = next

	return route


func _build_item_spawns(board_state: MazeData, reserved: Dictionary) -> Array[Dictionary]:
	var ordered_cells := _cells_by_distance(board_state.exit_cell, board_state)
	var item_ids := ["torch", "freeze", "compass", "extra_turns"]
	var item_spawns: Array[Dictionary] = []

	for item_id in item_ids:
		for cell in ordered_cells:
			if reserved.has(cell):
				continue
			if cell.distance_to(board_state.player_spawn) < 4.0:
				continue

			item_spawns.append({
				"item_id": item_id,
				"cell": cell,
			})
			reserved[cell] = true
			break

	return item_spawns
