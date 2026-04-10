extends Node2D

signal enemy_phase_finished(enemy_results)

const MINOTAUR_SCENE := preload("res://EnemyManager/Minotaur/Minotaur.tscn")

var board_state: MazeData


func setup_floor(next_board_state: MazeData) -> void:
	board_state = next_board_state
	for child in get_children():
		child.free()

	var minotaur = MINOTAUR_SCENE.instantiate()
	add_child(minotaur)
	minotaur.configure({
		"type": "minotaur",
		"cell": board_state.minotaur_spawn,
		"tint": Color(0.92, 0.24, 0.18, 1.0),
	}, board_state)


func begin_enemy_phase(player_cell: Vector2i) -> Array:
	if get_child_count() == 0:
		enemy_phase_finished.emit([])
		return []

	var occupied_cells: Array[Vector2i] = []
	var result: Dictionary = await get_child(0).take_turn(player_cell, occupied_cells)
	var results: Array = [result]
	enemy_phase_finished.emit(results)
	return results


func get_current_cell() -> Vector2i:
	if get_child_count() == 0:
		return Vector2i.ZERO
	return get_child(0).current_cell


func set_cell_immediate(cell: Vector2i) -> void:
	if get_child_count() == 0:
		return
	get_child(0).current_cell = cell
	get_child(0).position = board_state.to_world(cell)


func update_visibility(_visible_cells: Array[Vector2i]) -> void:
	for child in get_children():
		child.visible = true
