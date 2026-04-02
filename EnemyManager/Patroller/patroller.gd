extends "res://EnemyManager/enemy_base.gd"


func _ready() -> void:
	enemy_type = "patroller"
	super._ready()


func choose_target_cell(_player_cell: Vector2i, occupied_lookup: Dictionary) -> Vector2i:
	if patrol_route.size() <= 1:
		return current_cell

	var next_index := patrol_index + patrol_direction
	if next_index < 0 or next_index >= patrol_route.size():
		patrol_direction *= -1
		next_index = patrol_index + patrol_direction

	var target_cell: Vector2i = patrol_route[next_index]
	if not _can_enter(target_cell, occupied_lookup):
		patrol_direction *= -1
		next_index = patrol_index + patrol_direction
		if next_index < 0 or next_index >= patrol_route.size():
			return current_cell
		target_cell = patrol_route[next_index]
		if not _can_enter(target_cell, occupied_lookup):
			return current_cell

	patrol_index = next_index
	return target_cell
