extends RefCounted
class_name ZoneSpawnController

const ZoneSpawnerRuntimeRegistryScript := preload("res://EnemyManager/zone_spawner_runtime_registry.gd")
const ZoneSpawnerSystemScript := preload("res://EnemyManager/zone_spawner_system.gd")

var board_state: MazeData
var _runtime_registry = ZoneSpawnerRuntimeRegistryScript.new()


func setup(next_board_state: MazeData) -> void:
	board_state = next_board_state
	_runtime_registry.clear()
	if board_state == null:
		return

	for spawner_data in board_state.get_escape_zone_spawners():
		_runtime_registry.register_spawner(spawner_data)


func build_state_snapshot() -> Array[Dictionary]:
	var snapshots: Array[Dictionary] = []
	for record in _runtime_registry.records:
		snapshots.append(record.build_state_snapshot())
	return snapshots


func restore_state_snapshot(raw_states) -> void:
	_runtime_registry.clear()
	var board_spawners: Array[Dictionary] = []
	if board_state != null:
		board_spawners = board_state.get_escape_zone_spawners()
	for index in range(raw_states.size()):
		var entry = raw_states[index]
		if not entry is Dictionary:
			continue
		var config: Dictionary = entry.get("config", {})
		if config.is_empty():
			if index < board_spawners.size():
				config = board_spawners[index].duplicate(true)
			else:
				for candidate in board_spawners:
					if String(candidate.get("id", "")) == String(entry.get("id", "")):
						config = candidate.duplicate(true)
						break
		var record = _runtime_registry.register_spawner(config)
		record.restore_from_snapshot(entry)


func warning_cells(player_cell: Vector2i, occupied_cells: Array[Vector2i]) -> Array[Vector2i]:
	if board_state == null:
		return []
	return ZoneSpawnerSystemScript.warning_cells(_runtime_registry, player_cell, occupied_cells)


func advance(player_cell: Vector2i, occupied_cells: Array[Vector2i]) -> Array[Dictionary]:
	if board_state == null:
		return []
	return ZoneSpawnerSystemScript.advance(_runtime_registry, player_cell, occupied_cells)
