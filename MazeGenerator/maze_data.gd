extends RefCounted
class_name MazeData

var floor_index: int = 1
var width: int = 0
var height: int = 0
var cell_size: int = 16
var wall_density: float = 0.0
var base_visibility_radius: int = 4
var torch_bonus_radius: int = 2
var turn_limit: int = 60
var wall_cells: Array[Vector2i] = []
var floor_cells: Array[Vector2i] = []
var horizontal_walls: Array[Vector2i] = []
var vertical_walls: Array[Vector2i] = []
var player_spawn: Vector2i = Vector2i.ZERO
var exit_cell: Vector2i = Vector2i.ZERO
var key_cell: Vector2i = Vector2i.ZERO
var enemy_spawns: Array[Dictionary] = []
var item_spawns: Array[Dictionary] = []

var _floor_lookup: Dictionary = {}
var _horizontal_wall_lookup: Dictionary = {}
var _vertical_wall_lookup: Dictionary = {}


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


func remove_horizontal_wall(edge: Vector2i) -> void:
	if not _horizontal_wall_lookup.has(edge):
		return
	_horizontal_wall_lookup.erase(edge)
	horizontal_walls.erase(edge)


func add_vertical_wall(edge: Vector2i) -> void:
	if _vertical_wall_lookup.has(edge):
		return
	vertical_walls.append(edge)
	_vertical_wall_lookup[edge] = true


func remove_vertical_wall(edge: Vector2i) -> void:
	if not _vertical_wall_lookup.has(edge):
		return
	_vertical_wall_lookup.erase(edge)
	vertical_walls.erase(edge)


func has_horizontal_wall(edge: Vector2i) -> bool:
	return _horizontal_wall_lookup.has(edge)


func has_vertical_wall(edge: Vector2i) -> bool:
	return _vertical_wall_lookup.has(edge)


func has_wall_between(a: Vector2i, b: Vector2i) -> bool:
	var delta := b - a
	if abs(delta.x) + abs(delta.y) != 1:
		return true

	if delta.x != 0:
		var vertical_edge := Vector2i(max(a.x, b.x), a.y)
		return has_vertical_wall(vertical_edge)

	var horizontal_edge := Vector2i(a.x, max(a.y, b.y))
	return has_horizontal_wall(horizontal_edge)


func can_step(a: Vector2i, b: Vector2i) -> bool:
	if not is_walkable(a) or not is_walkable(b):
		return false
	return not has_wall_between(a, b)


func get_cardinal_neighbors(cell: Vector2i) -> Array[Vector2i]:
	var neighbors: Array[Vector2i] = []
	var directions := [
		Vector2i.LEFT,
		Vector2i.RIGHT,
		Vector2i.UP,
		Vector2i.DOWN,
	]

	for direction in directions:
		var next: Vector2i = cell + direction
		if can_step(cell, next):
			neighbors.append(next)

	return neighbors


func build_floor_lookup() -> Dictionary:
	return _floor_lookup
