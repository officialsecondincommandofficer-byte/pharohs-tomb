extends Node2D

@export var fill_color: Color = Color(0.62, 0.12, 0.08, 0.28)
@export var line_color: Color = Color(0.95, 0.74, 0.34, 0.95)
@export var line_width: float = 2.0

var _board_state: MazeData


func render_traps(board_state: MazeData) -> void:
	_board_state = board_state
	queue_redraw()


func _draw() -> void:
	if _board_state == null:
		return

	var cell_size: float = float(_board_state.cell_size)
	for cell in _board_state.trap_cells:
		var origin := Vector2(float(cell.x) * cell_size, float(cell.y) * cell_size)
		var rect := Rect2(origin, Vector2.ONE * cell_size)
		draw_rect(rect, fill_color)

		var inset := cell_size * 0.24
		var top_left := origin + Vector2(inset, inset)
		var top_right := origin + Vector2(cell_size - inset, inset)
		var bottom_left := origin + Vector2(inset, cell_size - inset)
		var bottom_right := origin + Vector2(cell_size - inset, cell_size - inset)
		draw_line(top_left, bottom_right, line_color, line_width)
		draw_line(top_right, bottom_left, line_color, line_width)
