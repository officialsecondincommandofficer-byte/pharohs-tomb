extends "res://EnemyManager/enemy_base.gd"

func _ready() -> void:
	enemy_type = "patroller"
	super._ready()


func _build_behavior_state_snapshot() -> Dictionary:
	return {
		"patrol_index": patrol_index,
		"patrol_direction": patrol_direction,
	}


func _restore_behavior_state_snapshot(state: Dictionary) -> void:
	patrol_index = clampi(int(state.get("patrol_index", patrol_index)), 0, max(patrol_route.size() - 1, 0))
	patrol_direction = 1 if int(state.get("patrol_direction", patrol_direction)) >= 0 else -1
