extends RefCounted
class_name EnemyRuntimeRecord


var enemy
var config: Dictionary = {}
var enemy_type: String = "enemy"
var spawn_order: int = 0
var traits: Array[String] = []
var current_cell: Vector2i = Vector2i.ZERO
var is_dead: bool = false
var shared_state: Dictionary = {}
var behavior_state: Dictionary = {}


func bind_enemy(next_enemy):
	enemy = next_enemy
	sync_from_enemy()
	return self


func sync_from_enemy() -> void:
	if enemy == null:
		return
	var snapshot: Dictionary = enemy.build_state_snapshot()
	config = snapshot.get("config", {}).duplicate(true)
	enemy_type = enemy.enemy_type
	spawn_order = enemy.spawn_order
	traits = enemy.traits.duplicate()
	current_cell = snapshot.get("cell", enemy.current_cell)
	is_dead = not bool(snapshot.get("alive", not enemy.is_dead))
	shared_state = snapshot.get("shared_state", {}).duplicate(true)
	behavior_state = snapshot.get("behavior_state", {}).duplicate(true)


func occupies_cell() -> bool:
	return not is_dead


func has_trait(trait_name: String) -> bool:
	return traits.has(trait_name)


func mark_dead() -> void:
	is_dead = true
	if enemy != null:
		apply_to_enemy()


func move_to_cell(next_cell: Vector2i) -> void:
	current_cell = next_cell


func restore_to_cell(cell: Vector2i, alive: bool) -> void:
	current_cell = cell
	is_dead = not alive
	if enemy != null:
		apply_to_enemy()


func restore_from_snapshot(snapshot: Dictionary) -> void:
	config = snapshot.get("config", config).duplicate(true)
	current_cell = snapshot.get("cell", current_cell)
	is_dead = not bool(snapshot.get("alive", not is_dead))
	var legacy_state: Dictionary = snapshot.get("state", {})
	shared_state = snapshot.get("shared_state", legacy_state).duplicate(true)
	behavior_state = snapshot.get("behavior_state", legacy_state).duplicate(true)
	if enemy != null:
		apply_to_enemy()


func apply_to_enemy() -> void:
	if enemy == null:
		return
	enemy.restore_from_state(
		{
			"cell": current_cell,
			"alive": not is_dead,
			"shared_state": shared_state.duplicate(true),
			"behavior_state": behavior_state.duplicate(true),
		}
	)


func build_state_snapshot() -> Dictionary:
	return {
		"config": config.duplicate(true),
		"cell": current_cell,
		"alive": not is_dead,
		"shared_state": shared_state.duplicate(true),
		"behavior_state": behavior_state.duplicate(true),
	}


func config_string(key: String, fallback: String = "") -> String:
	return String(config.get(key, fallback))


func config_int(key: String, fallback: int = 0) -> int:
	return int(config.get(key, fallback))


func component(component_name: String) -> Dictionary:
	var components: Dictionary = config.get("ecs_components", {})
	if components.has(component_name) and components[component_name] is Dictionary:
		return components[component_name]
	return {}


func component_string(component_name: String, key: String, fallback: String) -> String:
	return String(component(component_name).get(key, fallback))


func component_int(component_name: String, key: String, fallback: int) -> int:
	return int(component(component_name).get(key, fallback))
