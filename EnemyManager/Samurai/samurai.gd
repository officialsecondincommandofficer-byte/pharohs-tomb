extends "res://EnemyManager/enemy_base.gd"

const ROTATION_DIRECTIONS: Array[Vector2i] = [
	Vector2i.UP,
	Vector2i.RIGHT,
	Vector2i.DOWN,
	Vector2i.LEFT,
]

var facing_index: int = 2
var display_facing_index: int = 2
var attack_phase: int = -1
var turns_until_dash: int = 0


func _ready() -> void:
	enemy_type = "samurai"
	super._ready()
	_apply_facing()


func configure(spawn_data: Dictionary, next_board_state) -> void:
	super.configure(spawn_data, next_board_state)
	facing_index = posmod(runtime_config.facing_index, ROTATION_DIRECTIONS.size())
	display_facing_index = facing_index
	attack_phase = -1
	turns_until_dash = 0
	_apply_facing()


func _build_behavior_state_snapshot() -> Dictionary:
	return {
		"facing_index": facing_index,
		"display_facing_index": display_facing_index,
		"attack_phase": attack_phase,
		"turns_until_dash": turns_until_dash,
	}


func _restore_behavior_state_snapshot(state: Dictionary) -> void:
	facing_index = posmod(int(state.get("facing_index", facing_index)), ROTATION_DIRECTIONS.size())
	display_facing_index = posmod(int(state.get("display_facing_index", facing_index)), ROTATION_DIRECTIONS.size())
	attack_phase = int(state.get("attack_phase", attack_phase))
	turns_until_dash = int(state.get("turns_until_dash", turns_until_dash))
	_apply_facing()


func _apply_facing() -> void:
	_update_facing(ROTATION_DIRECTIONS[display_facing_index])
