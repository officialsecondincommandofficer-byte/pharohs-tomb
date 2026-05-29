extends RefCounted
class_name EnemySpawnData


static func coerce_enemy_spawn_array(raw_value, fallback_cell: Vector2i, allow_empty: bool = false) -> Array[Dictionary]:
	var coerced: Array[Dictionary] = []
	for entry in raw_value:
		if not entry is Dictionary:
			continue
		var spawn: Dictionary = entry.duplicate(true)
		spawn["type"] = String(spawn.get("type", "greedy_chaser"))
		spawn["cell"] = coerce_vector2i(spawn.get("cell", fallback_cell))
		spawn["move_priority"] = String(spawn.get("move_priority", "horizontal"))
		spawn["step_count"] = int(spawn.get("step_count", 2))
		spawn["facing_index"] = int(spawn.get("facing_index", 2))
		spawn["traits"] = coerce_string_array(spawn.get("traits", []))
		coerced.append(spawn)

	if coerced.is_empty() and not allow_empty:
		coerced.append(default_greedy_chaser(fallback_cell))
	return coerced


static func default_greedy_chaser(cell: Vector2i) -> Dictionary:
	return {
		"type": "greedy_chaser",
		"cell": cell,
		"move_priority": "horizontal",
		"step_count": 2,
		"facing_index": 2,
		"traits": [],
	}


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
