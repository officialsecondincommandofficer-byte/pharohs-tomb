extends "res://EnemyManager/enemy_base.gd"

var wake_goal_distance: int = -1
var lifetime_turns: int = -1
var turns_remaining: int = -1
var activated := true


func _ready() -> void:
	enemy_type = "chaser"
	super._ready()


func configure(spawn_data: Dictionary, next_board_state) -> void:
	super.configure(spawn_data, next_board_state)
	wake_goal_distance = runtime_config.wake_goal_distance
	lifetime_turns = runtime_config.lifetime_turns
	turns_remaining = lifetime_turns
	activated = wake_goal_distance < 0


func _build_shared_state_snapshot() -> Dictionary:
	return {
		"activated": activated,
		"turns_remaining": turns_remaining,
	}


func _restore_shared_state_snapshot(state: Dictionary) -> void:
	activated = bool(state.get("activated", activated))
	turns_remaining = int(state.get("turns_remaining", turns_remaining))
