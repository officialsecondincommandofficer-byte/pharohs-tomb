extends Node2D

@export var fill_color: Color = Color(0.16, 0.42, 0.55, 0.26)
@export var ring_color: Color = Color(0.46, 0.93, 0.99, 0.95)
@export var link_color: Color = Color(0.38, 0.82, 0.96, 0.35)
@export var enemy_fill_color: Color = Color(0.54, 0.18, 0.08, 0.24)
@export var enemy_ring_color: Color = Color(1.0, 0.55, 0.3, 0.95)
@export var enemy_link_color: Color = Color(0.95, 0.48, 0.18, 0.32)
@export var shared_fill_color: Color = Color(0.18, 0.46, 0.24, 0.22)
@export var shared_ring_color: Color = Color(0.58, 0.96, 0.62, 0.95)
@export var shared_link_color: Color = Color(0.42, 0.9, 0.5, 0.32)
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
		_draw_pair(pair, cell_size, fill_color, ring_color, link_color)
	for pair in _board_state.enemy_teleport_pairs:
		_draw_pair(pair, cell_size, enemy_fill_color, enemy_ring_color, enemy_link_color)
	for pair in _board_state.shared_teleport_pairs:
		_draw_pair(pair, cell_size, shared_fill_color, shared_ring_color, shared_link_color)


func _draw_pair(pair: Dictionary, cell_size: float, endpoint_fill: Color, endpoint_ring: Color, endpoint_link: Color) -> void:
	var a: Vector2i = pair.get("a", Vector2i.ZERO)
	var b: Vector2i = pair.get("b", Vector2i.ZERO)
	var center_a := _board_state.to_world(a)
	var center_b := _board_state.to_world(b)
	draw_line(center_a, center_b, endpoint_link, 1.5)
	_draw_endpoint(center_a, cell_size, endpoint_fill, endpoint_ring)
	_draw_endpoint(center_b, cell_size, endpoint_fill, endpoint_ring)


func _draw_endpoint(center: Vector2, cell_size: float, endpoint_fill: Color, endpoint_ring: Color) -> void:
	var radius := cell_size * 0.28
	draw_circle(center, radius, endpoint_fill)
	draw_arc(center, radius + 1.0, 0.0, TAU, 24, endpoint_ring, ring_width)
