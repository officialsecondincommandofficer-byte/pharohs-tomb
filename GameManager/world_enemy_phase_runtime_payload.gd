extends RefCounted
class_name WorldEnemyPhaseRuntimePayload

var enemy_snapshots: Array[Dictionary] = []
var spawner_snapshots: Array[Dictionary] = []
var dynamic_spawn_order: int = 0


func configure(
	next_enemy_snapshots: Array[Dictionary],
	next_spawner_snapshots: Array[Dictionary],
	next_dynamic_spawn_order: int
) -> WorldEnemyPhaseRuntimePayload:
	enemy_snapshots = _duplicate_dictionary_array(next_enemy_snapshots)
	spawner_snapshots = _duplicate_dictionary_array(next_spawner_snapshots)
	dynamic_spawn_order = next_dynamic_spawn_order
	return self


func from_dictionary(payload: Dictionary) -> WorldEnemyPhaseRuntimePayload:
	return configure(
		_duplicate_dictionary_array(payload.get("enemies", [])),
		_duplicate_dictionary_array(payload.get("spawner_states", [])),
		int(payload.get("dynamic_spawn_order", 0))
	)


func to_dictionary() -> Dictionary:
	return {
		"enemies": _duplicate_dictionary_array(enemy_snapshots),
		"spawner_states": _duplicate_dictionary_array(spawner_snapshots),
		"dynamic_spawn_order": dynamic_spawn_order,
	}


func duplicate_payload() -> WorldEnemyPhaseRuntimePayload:
	return get_script().new().configure(enemy_snapshots, spawner_snapshots, dynamic_spawn_order)


func alive_enemy_cells() -> Array[Vector2i]:
	var cells: Array[Vector2i] = []
	for enemy_state in enemy_snapshots:
		if not bool(enemy_state.get("alive", true)):
			continue
		var cell = enemy_state.get("cell", Vector2i.ZERO)
		if cell is Vector2i:
			cells.append(cell)
		elif cell is Vector2:
			cells.append(Vector2i(int(cell.x), int(cell.y)))
		elif cell is Array and cell.size() >= 2:
			cells.append(Vector2i(int(cell[0]), int(cell[1])))
	return cells


func first_enemy_cell() -> Vector2i:
	var enemy_cells := alive_enemy_cells()
	if enemy_cells.is_empty():
		return Vector2i.ZERO
	return enemy_cells[0]


static func legacy_from_snapshot(snapshot: Dictionary) -> WorldEnemyPhaseRuntimePayload:
	var enemies: Array[Dictionary] = []
	var legacy_cells = snapshot.get("enemies", [])
	if legacy_cells.is_empty() and snapshot.has("minotaur"):
		legacy_cells = [snapshot["minotaur"]]

	for enemy_cell in legacy_cells:
		enemies.append({
			"cell": enemy_cell,
			"alive": true,
			"config": {},
		})

	return load("res://GameManager/world_enemy_phase_runtime_payload.gd").new().configure(enemies, [], enemies.size())


static func _duplicate_dictionary_array(entries) -> Array[Dictionary]:
	var duplicated: Array[Dictionary] = []
	for entry in entries:
		if entry is Dictionary:
			duplicated.append(entry.duplicate(true))
	return duplicated
