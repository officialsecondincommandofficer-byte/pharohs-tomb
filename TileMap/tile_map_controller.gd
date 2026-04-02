extends Node2D

const TILE_SOURCE_ID := 1
const WALL_TILE := Vector2i(0, 0)
const FLOOR_TILE := Vector2i(1, 0)
const EXIT_LOCKED_TILE := Vector2i(2, 0)
const EXIT_UNLOCKED_TILE := Vector2i(3, 0)

@onready var floor_layer: TileMapLayer = $FloorLayer
@onready var wall_layer: TileMapLayer = $WallLayer
@onready var goal_layer: TileMapLayer = $GoalLayer
@onready var floor_checker_overlay: Node2D = $FloorCheckerOverlay
@onready var thin_wall_overlay: Node2D = $ThinWallOverlay

var _board_state
var _exit_unlocked := false


func render_board(board_state, exit_unlocked: bool) -> void:
	_board_state = board_state
	_exit_unlocked = exit_unlocked

	floor_layer.clear()
	wall_layer.clear()
	goal_layer.clear()
	thin_wall_overlay.call("render_walls", board_state)

	for floor_cell in board_state.floor_cells:
		floor_layer.set_cell(floor_cell, TILE_SOURCE_ID, FLOOR_TILE)

	floor_checker_overlay.call("render_checker", board_state)
	_draw_perimeter_border()
	_draw_exit()


func set_exit_unlocked(value: bool) -> void:
	_exit_unlocked = value
	_draw_exit()


func world_to_grid(pos: Vector2) -> Vector2i:
	if _board_state == null:
		return Vector2i.ZERO
	return _board_state.to_map(pos)


func grid_to_world(cell: Vector2i) -> Vector2:
	if _board_state == null:
		return Vector2.ZERO
	return _board_state.to_world(cell)


func _draw_exit() -> void:
	if _board_state == null:
		return

	goal_layer.clear()
	goal_layer.set_cell(
		_board_state.exit_cell,
		TILE_SOURCE_ID,
		EXIT_UNLOCKED_TILE if _exit_unlocked else EXIT_LOCKED_TILE
	)


func _draw_perimeter_border() -> void:
	if _board_state == null:
		return

	for x in range(-1, _board_state.width + 1):
		wall_layer.set_cell(Vector2i(x, -1), TILE_SOURCE_ID, WALL_TILE)
		wall_layer.set_cell(Vector2i(x, _board_state.height), TILE_SOURCE_ID, WALL_TILE)

	for y in _board_state.height:
		wall_layer.set_cell(Vector2i(-1, y), TILE_SOURCE_ID, WALL_TILE)
		wall_layer.set_cell(Vector2i(_board_state.width, y), TILE_SOURCE_ID, WALL_TILE)
