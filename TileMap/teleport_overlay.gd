extends Node2D

@export var fill_color: Color = Color(0.16, 0.42, 0.55, 0.26)
@export var ring_color: Color = Color(0.46, 0.93, 0.99, 0.95)
@export var link_color: Color = Color(0.38, 0.82, 0.96, 0.35)
@export var ring_width: float = 2.0

var _board_state: MazeData


func render_teleports(board_state: MazeData) -> void:
	_board_state = board_state
	queue_redraw()


func _draw() -> void:
	if _board_state == null:
		return

	var cell_size: float = float(_board_state.cell_size)
	for pair in _board_state.teleport_pairs:
		var a: Vector2i = pair.get("a", Vector2i.ZERO)
		var b: Vector2i = pair.get("b", Vector2i.ZERO)
		var center_a := _board_state.to_world(a)
		var center_b := _board_state.to_world(b)
		draw_line(center_a, center_b, link_color, 1.5)
		_draw_endpoint(center_a, cell_size)
		_draw_endpoint(center_b, cell_size)


func _draw_endpoint(center: Vector2, cell_size: float) -> void:
	var radius := cell_size * 0.28
	draw_circle(center, radius, fill_color)
	draw_arc(center, radius + 1.0, 0.0, TAU, 24, ring_color, ring_width)
