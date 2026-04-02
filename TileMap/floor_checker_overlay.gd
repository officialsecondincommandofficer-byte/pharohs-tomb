extends Node2D

@export var checker_color: Color = Color(0.74, 0.69, 0.58, 0.1)

var _board_state: MazeData


func render_checker(board_state: MazeData) -> void:
	_board_state = board_state
	queue_redraw()


func _draw() -> void:
	if _board_state == null:
		return

	var cell_size: float = float(_board_state.cell_size)
	for cell in _board_state.floor_cells:
		if (cell.x + cell.y) % 2 != 0:
			continue

		var rect := Rect2(
			Vector2(float(cell.x) * cell_size, float(cell.y) * cell_size),
			Vector2.ONE * cell_size
		)
		draw_rect(rect, checker_color)
