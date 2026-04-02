extends "res://EnemyManager/enemy_base.gd"


func _ready() -> void:
	enemy_type = "wanderer"
	super._ready()


func choose_target_cell(_player_cell: Vector2i, occupied_lookup: Dictionary) -> Vector2i:
	var options: Array[Vector2i] = []
	for neighbor in board_state.get_cardinal_neighbors(current_cell):
		if _can_enter(neighbor, occupied_lookup):
			options.append(neighbor)

	if options.is_empty():
		return current_cell

	return options[_rng.randi_range(0, options.size() - 1)]
