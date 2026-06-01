extends RefCounted
class_name EnemyRuntimeConfig


var enemy_type: String = "enemy"
var current_cell: Vector2i = Vector2i.ZERO
var spawn_order: int = 0
var traits: Array[String] = []
var canonical_archetype: String = ""
var ecs_schema_version: int = 1
var ecs_components: Dictionary = {}
var tint: Color = Color.WHITE

var role: String = ""
var scene_family: String = "chaser"
var movement_family: String = "greedy"
var move_priority: String = "horizontal"
var step_count: int = 1
var wake_goal_distance: int = -1
var lifetime_turns: int = -1
var spawn_delay_turns: int = 0
var respawn_delay_turns: int = 0
var facing_index: int = 2
var patrol_route: Array[Vector2i] = []
var patrol_mode: String = "ping_pong"
var behavior_seed: int = 0


func apply_spawn_data(spawn_data: Dictionary) -> EnemyRuntimeConfig:
	enemy_type = String(spawn_data.get("type", enemy_type))
	current_cell = _coerce_vector2i(spawn_data.get("cell", current_cell))
	spawn_order = int(spawn_data.get("spawn_order", spawn_order))
	traits = _coerce_string_array(spawn_data.get("traits", []))
	canonical_archetype = String(spawn_data.get("canonical_archetype", canonical_archetype))
	ecs_schema_version = int(spawn_data.get("ecs_schema_version", ecs_schema_version))
	ecs_components = spawn_data.get("ecs_components", {}).duplicate(true)
	tint = spawn_data.get("tint", tint)

	role = component_string("identity", "design_role", String(spawn_data.get("role", role)))
	scene_family = component_string("identity", "scene_family", scene_family)
	movement_family = component_string("movement", "family", String(spawn_data.get("movement_type", movement_family)))
	move_priority = component_string("movement", "move_priority", String(spawn_data.get("move_priority", move_priority)))
	step_count = component_int("movement", "step_count", int(spawn_data.get("step_count", step_count)))
	wake_goal_distance = component_int("activation", "wake_goal_distance", int(spawn_data.get("wake_goal_distance", wake_goal_distance)))
	lifetime_turns = component_int("lifecycle", "lifetime_turns", int(spawn_data.get("lifetime_turns", lifetime_turns)))
	spawn_delay_turns = component_int("activation", "spawn_delay_turns", int(spawn_data.get("spawn_delay_turns", spawn_delay_turns)))
	respawn_delay_turns = component_int("activation", "respawn_delay_turns", int(spawn_data.get("respawn_delay_turns", respawn_delay_turns)))
	facing_index = component_int("movement", "facing_index", int(spawn_data.get("facing_index", facing_index)))
	behavior_seed = component_int("behavior", "seed", int(spawn_data.get("behavior_seed", behavior_seed)))
	patrol_mode = component_string("movement", "patrol_mode", String(spawn_data.get("patrol_mode", patrol_mode)))

	patrol_route.clear()
	var raw_patrol_route: Array = component_array("movement", "patrol_route", spawn_data.get("patrol_route", [current_cell]))
	for patrol_cell in raw_patrol_route:
		patrol_route.append(_coerce_vector2i(patrol_cell))
	if patrol_mode == "loop" and patrol_route.size() > 1 and patrol_route[0] == patrol_route[patrol_route.size() - 1]:
		patrol_route.remove_at(patrol_route.size() - 1)
	if patrol_route.is_empty():
		patrol_route.append(current_cell)
	return self


func component(component_name: String) -> Dictionary:
	if ecs_components.has(component_name) and ecs_components[component_name] is Dictionary:
		return ecs_components[component_name]
	return {}


func component_string(component_name: String, key: String, fallback: String) -> String:
	return String(component(component_name).get(key, fallback))


func component_int(component_name: String, key: String, fallback: int) -> int:
	return int(component(component_name).get(key, fallback))


func component_array(component_name: String, key: String, fallback) -> Array:
	var value = component(component_name).get(key, fallback)
	if value is Array:
		return value.duplicate(true)
	if fallback is Array:
		return fallback.duplicate(true)
	return []


func to_spawn_snapshot(cell: Vector2i) -> Dictionary:
	return {
		"type": enemy_type,
		"cell": cell,
		"spawn_order": spawn_order,
		"traits": traits.duplicate(),
		"canonical_archetype": canonical_archetype,
		"ecs_schema_version": ecs_schema_version,
		"ecs_components": ecs_components.duplicate(true),
		"role": role,
		"scene_family": scene_family,
		"movement_type": movement_family,
		"move_priority": move_priority,
		"step_count": step_count,
		"facing_index": facing_index,
		"wake_goal_distance": wake_goal_distance,
		"lifetime_turns": lifetime_turns,
		"spawn_delay_turns": spawn_delay_turns,
		"respawn_delay_turns": respawn_delay_turns,
		"patrol_route": patrol_route.duplicate(),
		"patrol_mode": patrol_mode,
		"behavior_seed": behavior_seed,
	}


static func _coerce_string_array(raw_value) -> Array[String]:
	var coerced: Array[String] = []
	for entry in raw_value:
		coerced.append(String(entry))
	return coerced


static func _coerce_vector2i(raw_value) -> Vector2i:
	if raw_value is Vector2i:
		return raw_value
	if raw_value is Vector2:
		return Vector2i(int(raw_value.x), int(raw_value.y))
	if raw_value is Array and raw_value.size() >= 2:
		return Vector2i(int(raw_value[0]), int(raw_value[1]))
	return Vector2i.ZERO
