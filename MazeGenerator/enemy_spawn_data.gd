extends RefCounted
class_name EnemySpawnData

const EnemySchemaBridgeScript := preload("res://Global/enemy_schema_bridge.gd")


static func coerce_enemy_spawn_array(raw_value, fallback_cell: Vector2i, allow_empty: bool = false) -> Array[Dictionary]:
	var coerced: Array[Dictionary] = []
	for entry in raw_value:
		if not entry is Dictionary:
			continue
		var spawn: Dictionary = entry.duplicate(true)
		var raw_type := String(spawn.get("type", "greedy_chaser"))
		spawn["type"] = EnemySchemaBridgeScript.resolve_enemy_type(raw_type)
		spawn["cell"] = coerce_vector2i(spawn.get("cell", fallback_cell))
		spawn["role"] = EnemySchemaBridgeScript.resolved_enemy_role(
			raw_type,
			String(spawn.get("move_priority", "horizontal")),
			coerce_string_array(spawn.get("traits", [])),
			String(spawn.get("role", ""))
		)
		spawn["movement_type"] = EnemySchemaBridgeScript.resolved_movement_type(
			raw_type,
			String(spawn.get("role", "")),
			String(spawn.get("movement_type", ""))
		)
		spawn["move_priority"] = String(spawn.get("move_priority", "horizontal"))
		spawn["step_count"] = int(spawn.get("step_count", 2))
		spawn["facing_index"] = int(spawn.get("facing_index", 2))
		spawn["traits"] = coerce_string_array(spawn.get("traits", []))
		spawn["wake_goal_distance"] = int(spawn.get("wake_goal_distance", -1))
		spawn["lifetime_turns"] = int(spawn.get("lifetime_turns", -1))
		spawn["spawn_delay_turns"] = int(spawn.get("spawn_delay_turns", 0))
		spawn["respawn_delay_turns"] = int(spawn.get("respawn_delay_turns", 0))
		spawn["patrol_mode"] = String(spawn.get("patrol_mode", "ping_pong"))
		spawn["patrol_route"] = normalize_patrol_route(
			coerce_vector2i_array(spawn.get("patrol_route", [])),
			spawn["patrol_mode"]
		)
		spawn["behavior_seed"] = int(spawn.get("behavior_seed", 0))
		var bridge_payload: Dictionary = EnemySchemaBridgeScript.build_bridge_payload(spawn)
		spawn["canonical_enemy_type"] = String(bridge_payload.get("canonical_enemy_type", spawn["type"]))
		spawn["canonical_archetype"] = String(bridge_payload.get("archetype_id", ""))
		spawn["ecs_schema_version"] = int(bridge_payload.get("schema_version", 1))
		spawn["ecs_components"] = bridge_payload.get("components", {}).duplicate(true)
		coerced.append(spawn)

	if coerced.is_empty() and not allow_empty:
		coerced.append(default_greedy_chaser(fallback_cell))
	return coerced


static func default_greedy_chaser(cell: Vector2i) -> Dictionary:
	var spawn := {
		"type": "greedy_chaser",
		"cell": cell,
		"role": "x_chaser",
		"movement_type": "greedy",
		"move_priority": "horizontal",
		"step_count": 2,
		"facing_index": 2,
		"traits": [],
		"wake_goal_distance": -1,
		"lifetime_turns": -1,
		"spawn_delay_turns": 0,
		"respawn_delay_turns": 0,
	}
	var bridge_payload: Dictionary = EnemySchemaBridgeScript.build_bridge_payload(spawn)
	spawn["canonical_enemy_type"] = String(bridge_payload.get("canonical_enemy_type", spawn["type"]))
	spawn["canonical_archetype"] = String(bridge_payload.get("archetype_id", ""))
	spawn["ecs_schema_version"] = int(bridge_payload.get("schema_version", 1))
	spawn["ecs_components"] = bridge_payload.get("components", {}).duplicate(true)
	return spawn


static func first_enemy_cell(enemy_spawns: Array[Dictionary], fallback_cell: Vector2i) -> Vector2i:
	if enemy_spawns.is_empty():
		return fallback_cell
	return coerce_vector2i(enemy_spawns[0].get("cell", fallback_cell))


static func coerce_vector2i(raw_value) -> Vector2i:
	if raw_value is Vector2i:
		return raw_value
	if raw_value is Vector2:
		return Vector2i(int(raw_value.x), int(raw_value.y))
	if raw_value is Array and raw_value.size() >= 2:
		return Vector2i(int(raw_value[0]), int(raw_value[1]))
	return Vector2i.ZERO


static func coerce_string_array(raw_value) -> Array[String]:
	var coerced: Array[String] = []
	for entry in raw_value:
		coerced.append(String(entry))
	return coerced


static func coerce_vector2i_array(raw_value) -> Array[Vector2i]:
	var coerced: Array[Vector2i] = []
	for entry in raw_value:
		coerced.append(coerce_vector2i(entry))
	return coerced


static func normalize_patrol_route(route: Array[Vector2i], patrol_mode: String) -> Array[Vector2i]:
	var normalized := route.duplicate()
	if patrol_mode == "loop" and normalized.size() > 1 and normalized[0] == normalized[normalized.size() - 1]:
		normalized.remove_at(normalized.size() - 1)
	return normalized
