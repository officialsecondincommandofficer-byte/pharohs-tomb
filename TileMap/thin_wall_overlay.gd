extends Node2D

@export var wall_color: Color = Color(0.16, 0.1, 0.06, 0.95)
@export var player_only_wall_color: Color = Color(0.18, 0.62, 0.92, 0.92)
@export var enemy_only_wall_color: Color = Color(0.85, 0.73, 0.24, 0.92)
@export var wall_thickness: float = 3.0

var _board_state: MazeData


func render_walls(board_state: MazeData) -> void:
	_board_state = board_state
	queue_redraw()


func _draw() -> void:
	if _board_state == null:
		return

	var cell_size: float = float(_board_state.cell_size)
	var thickness: float = wall_thickness
	var half_thickness: float = thickness * 0.5

	_draw_horizontal_edges(_board_state.horizontal_walls, cell_size, thickness, half_thickness, wall_color)
	_draw_vertical_edges(_board_state.vertical_walls, cell_size, thickness, half_thickness, wall_color)
	_draw_horizontal_edges(_board_state.player_horizontal_walls, cell_size, thickness, half_thickness, player_only_wall_color)
	_draw_vertical_edges(_board_state.player_vertical_walls, cell_size, thickness, half_thickness, player_only_wall_color)
	_draw_horizontal_edges(_board_state.enemy_horizontal_walls, cell_size, thickness, half_thickness, enemy_only_wall_color)
	_draw_vertical_edges(_board_state.enemy_vertical_walls, cell_size, thickness, half_thickness, enemy_only_wall_color)


func _draw_horizontal_edges(edges: Array[Vector2i], cell_size: float, thickness: float, half_thickness: float, color: Color) -> void:
	for edge in edges:
		if edge.y <= 0 or edge.y >= _board_state.height:
			continue
		var edge_position := Vector2(float(edge.x) * cell_size, float(edge.y) * cell_size - half_thickness)
		draw_rect(Rect2(edge_position, Vector2(cell_size, thickness)), color)


func _draw_vertical_edges(edges: Array[Vector2i], cell_size: float, thickness: float, half_thickness: float, color: Color) -> void:
	for edge in edges:
		if edge.x <= 0 or edge.x >= _board_state.width:
			continue
		var vertical_position := Vector2(float(edge.x) * cell_size - half_thickness, float(edge.y) * cell_size)
		draw_rect(Rect2(vertical_position, Vector2(thickness, cell_size)), color)
