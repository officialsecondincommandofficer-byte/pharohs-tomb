extends Node2D

signal enemy_phase_finished(enemy_results)

const CHASER_SCENE := preload("res://EnemyManager/Chaser/Chaser.tscn")
const PATROLLER_SCENE := preload("res://EnemyManager/Patroller/Patroller.tscn")
const WANDERER_SCENE := preload("res://EnemyManager/Wanderer/Wanderer.tscn")

var board_state


func setup_floor(next_board_state) -> void:
	board_state = next_board_state
	for child in get_children():
		child.free()

	for spawn_data in board_state.enemy_spawns:
		var enemy_scene: PackedScene = _scene_for_type(spawn_data["type"])
		var enemy = enemy_scene.instantiate()
		add_child(enemy)
		enemy.configure(spawn_data, board_state)


func begin_enemy_phase(player_cell: Vector2i) -> void:
	var phase_results: Array = []

	for enemy in get_children():
		var occupied_cells: Array[Vector2i] = get_enemy_cells()
		var result: Dictionary = await enemy.take_turn(player_cell, occupied_cells)
		phase_results.append(result)
		if result["contact_player"]:
			break

	enemy_phase_finished.emit(phase_results)


func is_cell_occupied(cell: Vector2i) -> bool:
	for enemy in get_children():
		if enemy.current_cell == cell:
			return true
	return false


func get_enemy_cells() -> Array[Vector2i]:
	var cells: Array[Vector2i] = []
	for enemy in get_children():
		cells.append(enemy.current_cell)
	return cells


func update_visibility(visible_cells: Array[Vector2i]) -> void:
	var visible_lookup := {}
	for cell in visible_cells:
		visible_lookup[cell] = true

	for enemy in get_children():
		enemy.visible = visible_lookup.has(enemy.current_cell)


func _scene_for_type(enemy_type: String) -> PackedScene:
	match enemy_type:
		"chaser":
			return CHASER_SCENE
		"chaser_vertical":
			return CHASER_SCENE
		"patroller":
			return PATROLLER_SCENE
		"wanderer":
			return WANDERER_SCENE
		_:
			return CHASER_SCENE
