extends Node2D

var board_state
var _visible_lookup := {}
var _explored_lookup := {}
var _reveal_exit := false


func setup_floor(next_board_state) -> void:
	board_state = next_board_state
	_visible_lookup.clear()
	_explored_lookup.clear()
	_reveal_exit = false
	visible = false
	queue_redraw()


func update_visibility(player_cell: Vector2i, radius: int, reveal_exit: bool) -> Array[Vector2i]:
	_visible_lookup.clear()
	_explored_lookup.clear()
	_reveal_exit = false
	var visible_cells: Array[Vector2i] = []

	for y in board_state.height:
		for x in board_state.width:
			var cell := Vector2i(x, y)
			_visible_lookup[cell] = true
			_explored_lookup[cell] = true
			visible_cells.append(cell)

	queue_redraw()
	return visible_cells


func _draw() -> void:
	if board_state == null:
		return

	for y in board_state.height:
		for x in board_state.width:
			var cell := Vector2i(x, y)
			var top_left := Vector2(x * board_state.cell_size, y * board_state.cell_size)
			var rect := Rect2(top_left, Vector2.ONE * board_state.cell_size)

			if _visible_lookup.has(cell):
				continue
			if _explored_lookup.has(cell):
				draw_rect(rect, Color(0, 0, 0, 0.55), true)
			else:
				draw_rect(rect, Color(0, 0, 0, 0.95), true)

	if _reveal_exit:
		var exit_top_left := Vector2(
			board_state.exit_cell.x * board_state.cell_size,
			board_state.exit_cell.y * board_state.cell_size
		)
		draw_rect(
			Rect2(exit_top_left, Vector2.ONE * board_state.cell_size),
			Color(1.0, 0.85, 0.1, 0.25),
			true
		)
