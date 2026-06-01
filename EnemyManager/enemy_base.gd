extends CharacterBody2D

const EnemyRuntimeConfigScript := preload("res://EnemyManager/enemy_runtime_config.gd")

@export var enemy_type: String = "enemy"
@export var tint: Color = Color.WHITE
@export var move_duration: float = 0.12

@onready var anim: AnimatedSprite2D = $AnimatedSprite2D

var board_state
var runtime_config = EnemyRuntimeConfigScript.new()
var current_cell: Vector2i = Vector2i.ZERO
var spawn_order: int = 0
var traits: Array[String] = []
var canonical_archetype: String = ""
var ecs_schema_version: int = 1
var ecs_components: Dictionary = {}
var is_dead := false
var patrol_route: Array[Vector2i] = []
var patrol_index := 0
var patrol_direction := 1
var behavior_seed: int = 0


func _ready() -> void:
	anim.modulate = tint


func configure(spawn_data: Dictionary, next_board_state) -> void:
	board_state = next_board_state
	runtime_config = EnemyRuntimeConfigScript.new().apply_spawn_data(spawn_data)
	enemy_type = runtime_config.enemy_type
	spawn_order = runtime_config.spawn_order
	traits = runtime_config.traits.duplicate()
	canonical_archetype = runtime_config.canonical_archetype
	ecs_schema_version = runtime_config.ecs_schema_version
	ecs_components = runtime_config.ecs_components.duplicate(true)
	tint = runtime_config.tint
	current_cell = runtime_config.current_cell
	is_dead = false
	visible = true
	behavior_seed = runtime_config.behavior_seed
	patrol_route = runtime_config.patrol_route.duplicate()
	patrol_index = 0
	patrol_direction = 1
	position = board_state.to_world(current_cell)
	anim.modulate = tint

func present_move_to_cell(next_cell: Vector2i) -> void:
	if next_cell == current_cell:
		return
	var step_direction: Vector2i = next_cell - current_cell
	current_cell = next_cell
	_update_facing(step_direction)
	await _animate_to_world_position(board_state.to_world(current_cell))


func mark_dead() -> void:
	is_dead = true
	visible = false


func restore_to_cell(cell: Vector2i, alive: bool) -> void:
	current_cell = cell
	position = board_state.to_world(current_cell)
	is_dead = not alive
	visible = alive


func has_trait(trait_name: String) -> bool:
	return traits.has(trait_name)


func build_state_snapshot() -> Dictionary:
	return {
		"config": build_spawn_snapshot(),
		"cell": current_cell,
		"alive": not is_dead,
		"shared_state": _build_shared_state_snapshot(),
		"behavior_state": _build_behavior_state_snapshot(),
	}


func restore_from_state(enemy_state: Dictionary) -> void:
	var cell: Vector2i = enemy_state.get("cell", current_cell)
	var alive := bool(enemy_state.get("alive", true))
	restore_to_cell(cell, alive)
	var legacy_state: Dictionary = enemy_state.get("state", {})
	_restore_shared_state_snapshot(enemy_state.get("shared_state", legacy_state))
	_restore_behavior_state_snapshot(enemy_state.get("behavior_state", legacy_state))

func build_spawn_snapshot() -> Dictionary:
	var snapshot: Dictionary = runtime_config.to_spawn_snapshot(current_cell)
	snapshot["traits"] = traits.duplicate()
	snapshot["canonical_archetype"] = canonical_archetype
	snapshot["ecs_schema_version"] = ecs_schema_version
	snapshot["ecs_components"] = ecs_components.duplicate(true)
	return snapshot


func occupies_cell() -> bool:
	return not is_dead


func _ecs_component(component_name: String) -> Dictionary:
	return runtime_config.component(component_name)


func _ecs_string(component_name: String, key: String, fallback: String) -> String:
	return runtime_config.component_string(component_name, key, fallback)


func _ecs_int(component_name: String, key: String, fallback: int) -> int:
	return runtime_config.component_int(component_name, key, fallback)


func _ecs_array(component_name: String, key: String, fallback) -> Array:
	return runtime_config.component_array(component_name, key, fallback)


func _coerce_vector2i(raw_value) -> Vector2i:
	return EnemyRuntimeConfigScript._coerce_vector2i(raw_value)


func _build_shared_state_snapshot() -> Dictionary:
	return {}


func _restore_shared_state_snapshot(_state: Dictionary) -> void:
	return


func _build_behavior_state_snapshot() -> Dictionary:
	return {}


func _restore_behavior_state_snapshot(_state: Dictionary) -> void:
	return


func _can_enter(cell: Vector2i, occupied_lookup: Dictionary) -> bool:
	if not board_state.can_enemy_step(current_cell, cell):
		return false
	return not occupied_lookup.has(cell)


func _update_facing(direction: Vector2i) -> void:
	if direction.x > 0:
		anim.play("walk_right")
	elif direction.x < 0:
		anim.play("walk_left")
	elif direction.y > 0:
		anim.play("walk_downward")
	elif direction.y < 0:
		anim.play("walk_upward")


func _animate_to_world_position(target_position: Vector2) -> void:
	var tween: Tween = create_tween()
	tween.tween_property(self, "position", target_position, move_duration).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	await tween.finished
