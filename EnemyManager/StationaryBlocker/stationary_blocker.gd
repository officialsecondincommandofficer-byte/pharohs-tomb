extends "res://EnemyManager/enemy_base.gd"


func _ready() -> void:
	enemy_type = "stationary_blocker"
	super._ready()


func choose_target_cell(_player_cell: Vector2i, _occupied_lookup: Dictionary) -> Vector2i:
	return current_cell
