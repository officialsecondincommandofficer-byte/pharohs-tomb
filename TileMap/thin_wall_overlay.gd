extends Node2D

@export var wall_color: Color = Color(0.16, 0.1, 0.06, 0.95)
@export var player_only_wall_color: Color = Color(0.18, 0.62, 0.92, 0.92)
@export var enemy_only_wall_color: Color = Color(0.85, 0.73, 0.24, 0.92)
@export var one_way_passage_color: Color = Color(0.82, 0.31, 0.22, 0.95)
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
	_draw_one_way_passages(_board_state.one_way_passages, cell_size, one_way_passage_color)


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


func _draw_one_way_passages(passages: Array[Dictionary], cell_size: float, color: Color) -> void:
	var stripe_width: float = max(1.0, wall_thickness * 0.5)
	var edge_length: float = cell_size
	var stripe_offset: float = max(0.75, stripe_width * 0.5)
	for passage in passages:
		var from_cell: Vector2i = passage.get("from", Vector2i.ZERO) as Vector2i
		var to_cell: Vector2i = passage.get("to", Vector2i.ZERO) as Vector2i
		var from_center: Vector2 = Vector2(
			float(from_cell.x) * cell_size + cell_size * 0.5,
			float(from_cell.y) * cell_size + cell_size * 0.5
		)
		var to_center: Vector2 = Vector2(
			float(to_cell.x) * cell_size + cell_size * 0.5,
			float(to_cell.y) * cell_size + cell_size * 0.5
		)
		var direction: Vector2 = (to_center - from_center).normalized()
		if direction == Vector2.ZERO:
			continue
		var perpendicular: Vector2 = Vector2(-direction.y, direction.x)
		var edge_midpoint: Vector2 = (from_center + to_center) * 0.5
		var allowed_center: Vector2 = edge_midpoint - direction * stripe_offset
		var blocked_center: Vector2 = edge_midpoint + direction * stripe_offset
		var allowed_start: Vector2 = allowed_center - perpendicular * (edge_length * 0.5)
		var allowed_end: Vector2 = allowed_center + perpendicular * (edge_length * 0.5)
		var blocked_start: Vector2 = blocked_center - perpendicular * (edge_length * 0.5)
		var blocked_end: Vector2 = blocked_center + perpendicular * (edge_length * 0.5)
		draw_line(allowed_start, allowed_end, color, stripe_width)
		draw_line(blocked_start, blocked_end, wall_color, stripe_width)
