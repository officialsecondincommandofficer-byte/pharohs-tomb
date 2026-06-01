extends RefCounted
class_name ZoneSpawnerSystem

const INVALID_SPAWN_CELL := Vector2i(-9999, -9999)
const EnemySchemaBridge := preload("res://Global/enemy_schema_bridge.gd")


static func warning_cells(registry, player_cell: Vector2i, occupied_cells: Array[Vector2i]) -> Array[Vector2i]:
	var warning_cells: Array[Vector2i] = []
	for record in registry.records:
		if record.turns_until_spawn != 1:
			continue
		var spawn_cell: Vector2i = choose_spawner_cell(record.config, player_cell, occupied_cells)
		if spawn_cell == INVALID_SPAWN_CELL:
			continue
		warning_cells.append(spawn_cell)
	return warning_cells


static func advance(registry, player_cell: Vector2i, occupied_cells: Array[Vector2i]) -> Array[Dictionary]:
	var spawned_configs: Array[Dictionary] = []
	for record in registry.records:
		var next_turns_until_spawn: int = record.turns_until_spawn - 1
		if next_turns_until_spawn > 0:
			record.turns_until_spawn = next_turns_until_spawn
			continue

		var spawn_cell: Vector2i = choose_spawner_cell(record.config, player_cell, occupied_cells)
		if spawn_cell == INVALID_SPAWN_CELL:
			record.turns_until_spawn = 1
			continue

		spawned_configs.append(build_spawn_configuration(record.config, spawn_cell))
		occupied_cells.append(spawn_cell)
		record.turns_until_spawn = int(record.config.get("spawn_interval_turns", 2))
	return spawned_configs


static func build_spawn_configuration(spawner_config: Dictionary, spawn_cell: Vector2i) -> Dictionary:
	var spawn_config := {
		"type": String(spawner_config.get("enemy_type", "linked_escape_hunter")),
		"role": String(spawner_config.get("role", "linked_escape_hunter")),
		"movement_type": String(spawner_config.get("movement_type", "astar")),
		"cell": spawn_cell,
		"move_priority": String(spawner_config.get("move_priority", "horizontal")),
		"step_count": int(spawner_config.get("step_count", 2)),
		"facing_index": int(spawner_config.get("facing_index", 2)),
		"traits": spawner_config.get("traits", ["escape_linked"]),
		"wake_goal_distance": -1,
		"lifetime_turns": int(spawner_config.get("lifetime_turns", 3)),
		"patrol_route": spawner_config.get("patrol_route", []),
		"patrol_mode": String(spawner_config.get("patrol_mode", "ping_pong")),
		"behavior_seed": int(spawner_config.get("behavior_seed", 0)),
	}
	var bridge_payload: Dictionary = EnemySchemaBridge.build_bridge_payload(spawn_config)
	spawn_config["canonical_enemy_type"] = String(bridge_payload.get("canonical_enemy_type", spawn_config["type"]))
	spawn_config["canonical_archetype"] = String(bridge_payload.get("archetype_id", ""))
	spawn_config["ecs_schema_version"] = int(bridge_payload.get("schema_version", 1))
	spawn_config["ecs_components"] = bridge_payload.get("components", {}).duplicate(true)
	return spawn_config


static func choose_spawner_cell(spawner_config: Dictionary, player_cell: Vector2i, occupied_cells: Array[Vector2i]) -> Vector2i:
	var candidate_cells: Array = spawner_config.get("spawn_candidates", [])
	var occupied_lookup: Dictionary = {}
	for occupied_cell in occupied_cells:
		occupied_lookup[occupied_cell] = true

	var available: Array[Vector2i] = []
	for raw_candidate in candidate_cells:
		var candidate: Vector2i = raw_candidate
		if occupied_lookup.has(candidate):
			continue
		available.append(candidate)
	if available.is_empty():
		return INVALID_SPAWN_CELL

	available.sort_custom(func(a: Vector2i, b: Vector2i) -> bool:
		var a_distance: int = absi(a.x - player_cell.x) + absi(a.y - player_cell.y)
		var b_distance: int = absi(b.x - player_cell.x) + absi(b.y - player_cell.y)
		if a_distance == b_distance:
			if a.y == b.y:
				return a.x < b.x
			return a.y < b.y
		return a_distance > b_distance
	)
	return available[0]
