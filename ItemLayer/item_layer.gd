extends Node2D

signal item_collected(item_id)
signal item_used(item_result)

const KEY_SCENE := preload("res://ItemLayer/Key/Key.tscn")
const TORCH_SCENE := preload("res://ItemLayer/Torch/Torch.tscn")
const FREEZE_SCENE := preload("res://ItemLayer/Freeze/Freeze.tscn")
const COMPASS_SCENE := preload("res://ItemLayer/Compass/Compass.tscn")
const EXTRA_TURNS_SCENE := preload("res://ItemLayer/ExtraTurns/ExtraTurns.tscn")

var board_state


func setup_floor(next_board_state) -> void:
	board_state = next_board_state
	for child in get_children():
		child.free()

	_spawn_pickup(KEY_SCENE, board_state.key_cell)

	for spawn_data in board_state.item_spawns:
		_spawn_pickup(_scene_for_item(spawn_data["item_id"]), spawn_data["cell"])


func collect_item_at(cell: Vector2i) -> String:
	for child in get_children():
		if child.grid_cell != cell:
			continue

		var collected_item_id: String = child.item_id
		child.free()
		item_collected.emit(collected_item_id)
		return collected_item_id

	return ""


func notify_item_used(item_id: String, item_result: Dictionary) -> void:
	item_used.emit({
		"item_id": item_id,
		"result": item_result,
	})


func update_visibility(visible_cells: Array[Vector2i]) -> void:
	var visible_lookup := {}
	for cell in visible_cells:
		visible_lookup[cell] = true

	for child in get_children():
		child.visible = visible_lookup.has(child.grid_cell)


func _spawn_pickup(scene: PackedScene, cell: Vector2i) -> void:
	var pickup = scene.instantiate()
	add_child(pickup)
	pickup.configure(cell, board_state)


func _scene_for_item(item_id: String) -> PackedScene:
	match item_id:
		"torch":
			return TORCH_SCENE
		"freeze":
			return FREEZE_SCENE
		"compass":
			return COMPASS_SCENE
		"extra_turns":
			return EXTRA_TURNS_SCENE
		_:
			return KEY_SCENE
