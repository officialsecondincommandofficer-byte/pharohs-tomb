extends Node2D

@export var fill_color: Color = Color(0.96, 0.84, 0.22, 0.34)
@export var line_color: Color = Color(1.0, 0.93, 0.55, 0.95)
@export var line_width: float = 2.0

var _board_state: MazeData
var _warning_cells: Array[Vector2i] = []


func render_warnings(board_state: MazeData, warning_cells: Array[Vector2i]) -> void:
	_board_state = board_state
	_warning_cells = warning_cells.duplicate()
	queue_redraw()


func _draw() -> void:
	if _board_state == null:
		return

	var cell_size: float = float(_board_state.cell_size)
	for cell in _warning_cells:
		var origin := Vector2(float(cell.x) * cell_size, float(cell.y) * cell_size)
		var rect := Rect2(origin, Vector2.ONE * cell_size)
		draw_rect(rect, fill_color)

		var inset := cell_size * 0.18
		var inner_rect := Rect2(
			origin + Vector2.ONE * inset,
			Vector2.ONE * max(cell_size - inset * 2.0, 1.0)
		)
		draw_rect(inner_rect, line_color, false, line_width)
