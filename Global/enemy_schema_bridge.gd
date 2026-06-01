extends RefCounted
class_name EnemySchemaBridge


const SCHEMA_PATH := "res://Resources/DataSchemas/enemy_ecs_schema.json"

static var _schema_cache: Dictionary = {}


static func load_schema() -> Dictionary:
	if not _schema_cache.is_empty():
		return _schema_cache
	var raw_json := FileAccess.get_file_as_string(SCHEMA_PATH)
	var parsed = JSON.parse_string(raw_json)
	if parsed is Dictionary:
		_schema_cache = parsed
		return _schema_cache
	push_warning("Failed to load enemy ECS schema from %s" % SCHEMA_PATH)
	return {}


static func resolve_enemy_type(enemy_type: String) -> String:
	var schema := load_schema()
	var profile: Dictionary = schema.get("enemy_type_profiles", {}).get(enemy_type, {})
	return String(profile.get("canonical_enemy_type", enemy_type))


static func resolved_enemy_role(enemy_type: String, move_priority: String = "horizontal", traits: Array[String] = [], explicit_role: String = "") -> String:
	if not explicit_role.is_empty():
		return explicit_role
	if traits.has("escape_linked"):
		return "linked_escape_hunter"
	var schema := load_schema()
	var profile: Dictionary = schema.get("enemy_type_profiles", {}).get(enemy_type, {})
	var default_roles: Dictionary = profile.get("default_role_by_move_priority", {})
	if default_roles.has(move_priority):
		return String(default_roles.get(move_priority, enemy_type))
	return String(profile.get("default_role", enemy_type))


static func resolved_movement_type(enemy_type: String, role: String = "", explicit_movement_type: String = "") -> String:
	if not explicit_movement_type.is_empty():
		return explicit_movement_type
	var schema := load_schema()
	var resolved_role_name := role if not role.is_empty() else resolved_enemy_role(enemy_type)
	var role_profile: Dictionary = schema.get("role_profiles", {}).get(resolved_role_name, {})
	if not role_profile.is_empty():
		return String(role_profile.get("movement_type", "greedy"))
	return "greedy"


static func build_bridge_payload(spawn_data: Dictionary) -> Dictionary:
	var schema := load_schema()
	var traits: Array[String] = _coerce_string_array(spawn_data.get("traits", []))
	var enemy_type := String(spawn_data.get("type", "greedy_chaser"))
	var move_priority := String(spawn_data.get("move_priority", "horizontal"))
	var canonical_enemy_type: String = resolve_enemy_type(enemy_type)
	var role: String = resolved_enemy_role(
		enemy_type,
		move_priority,
		traits,
		String(spawn_data.get("role", ""))
	)
	var movement_type: String = resolved_movement_type(
		enemy_type,
		role,
		String(spawn_data.get("movement_type", ""))
	)
	var role_profile: Dictionary = _duplicate_dict(schema.get("role_profiles", {}).get(role, {}))
	var enemy_type_profile: Dictionary = schema.get("enemy_type_profiles", {}).get(enemy_type, {})
	var components: Dictionary = _duplicate_dict(role_profile.get("components", {}))
	var identity: Dictionary = _duplicate_dict(components.get("identity", {}))
	identity["canonical_enemy_type"] = canonical_enemy_type
	identity["scene_family"] = String(enemy_type_profile.get("scene_family", role_profile.get("scene_family", schema.get("default_scene_family", "chaser"))))
	components["identity"] = identity
	var movement: Dictionary = _duplicate_dict(components.get("movement", {}))
	movement["family"] = movement_type
	movement["step_count"] = int(spawn_data.get("step_count", 1))
	movement["move_priority"] = move_priority
	movement["facing_index"] = int(spawn_data.get("facing_index", 2))
	var patrol_route: Array = spawn_data.get("patrol_route", [])
	if patrol_route is Array and not patrol_route.is_empty():
		movement["patrol_route"] = patrol_route.duplicate(true)
		movement["patrol_mode"] = String(spawn_data.get("patrol_mode", "ping_pong"))
	components["movement"] = movement
	components["activation"] = {
		"wake_goal_distance": int(spawn_data.get("wake_goal_distance", -1)),
		"spawn_delay_turns": int(spawn_data.get("spawn_delay_turns", 0)),
		"respawn_delay_turns": int(spawn_data.get("respawn_delay_turns", 0)),
	}
	components["lifecycle"] = {
		"lifetime_turns": int(spawn_data.get("lifetime_turns", -1)),
	}
	var behavior_seed: int = int(spawn_data.get("behavior_seed", 0))
	if behavior_seed != 0:
		components["behavior"] = {"seed": behavior_seed}
	var trait_components: Dictionary = schema.get("trait_components", {})
	for trait_name in traits:
		var trait_payload: Dictionary = _duplicate_dict(trait_components.get(trait_name, {}))
		for component_name in trait_payload.keys():
			var merged_component: Dictionary = _duplicate_dict(components.get(component_name, {}))
			merged_component.merge(trait_payload[component_name], true)
			components[component_name] = merged_component
	return {
		"schema_version": int(schema.get("schema_version", 1)),
		"canonical_enemy_type": canonical_enemy_type,
		"archetype_id": String(role_profile.get("archetype_id", "enemy.%s" % role)),
		"scene_family": identity["scene_family"],
		"legacy": {
			"enemy_type": enemy_type,
			"role": role,
			"movement_type": movement_type,
			"traits": traits.duplicate(),
		},
		"components": components,
	}


static func tint_for_spawn(spawn_data: Dictionary) -> Color:
	if spawn_data.has("tint"):
		return spawn_data["tint"]
	var payload: Dictionary = build_bridge_payload(spawn_data)
	var schema := load_schema()
	var role_name := String(payload.get("legacy", {}).get("role", ""))
	var role_profile: Dictionary = schema.get("role_profiles", {}).get(role_name, {})
	var tint_values: Array = role_profile.get("tint", [])
	if tint_values.size() == 4:
		return Color(float(tint_values[0]), float(tint_values[1]), float(tint_values[2]), float(tint_values[3]))
	var default_tints: Dictionary = schema.get("default_tints", {})
	var move_priority := String(spawn_data.get("move_priority", "horizontal"))
	var fallback_tint: Array = default_tints.get(move_priority, default_tints.get("horizontal", [0.92, 0.24, 0.18, 1.0]))
	return Color(float(fallback_tint[0]), float(fallback_tint[1]), float(fallback_tint[2]), float(fallback_tint[3]))


static func scene_family_for_spawn(spawn_data: Dictionary) -> String:
	return String(build_bridge_payload(spawn_data).get("scene_family", "chaser"))


static func _coerce_string_array(raw_value) -> Array[String]:
	var coerced: Array[String] = []
	for entry in raw_value:
		coerced.append(String(entry))
	return coerced


static func _duplicate_dict(value) -> Dictionary:
	if value is Dictionary:
		return value.duplicate(true)
	return {}
