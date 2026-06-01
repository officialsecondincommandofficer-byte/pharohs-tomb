extends Node2D

signal enemy_phase_finished(enemy_results)

const ZoneSpawnControllerScript := preload("res://EnemyManager/zone_spawn_controller.gd")
const EnemySchemaBridge := preload("res://Global/enemy_schema_bridge.gd")
const EnemyContactSystemScript := preload("res://EnemyManager/enemy_contact_system.gd")
const EnemyRuntimeRegistryScript := preload("res://EnemyManager/enemy_runtime_registry.gd")
const EnemyTurnSystemScript := preload("res://EnemyManager/enemy_turn_system.gd")
const CHASER_SCENE := preload("res://EnemyManager/Chaser/Chaser.tscn")
const MINOTAUR_SCENE := preload("res://EnemyManager/Minotaur/Minotaur.tscn")
const PATROLLER_SCENE := preload("res://EnemyManager/Patroller/Patroller.tscn")
const SAMURAI_SCENE := preload("res://EnemyManager/Samurai/Samurai.tscn")
const STATIONARY_BLOCKER_SCENE := preload("res://EnemyManager/StationaryBlocker/StationaryBlocker.tscn")
const WANDERER_SCENE := preload("res://EnemyManager/Wanderer/Wanderer.tscn")
var board_state: MazeData
var _dynamic_spawn_order: int = 0
var _runtime_registry = EnemyRuntimeRegistryScript.new()
var _zone_spawn_controller = ZoneSpawnControllerScript.new()


func setup_floor(next_board_state: MazeData) -> void:
	board_state = next_board_state
	_runtime_registry.clear()
	for child in get_children():
		child.free()

	for spawn_index in range(board_state.enemy_spawns.size()):
		_spawn_enemy_from_data(board_state.enemy_spawns[spawn_index], spawn_index)

	_zone_spawn_controller.setup(board_state)
	_dynamic_spawn_order = board_state.enemy_spawns.size()
	_refresh_enemy_intents()


func begin_enemy_phase(player_cell: Vector2i) -> Array:
	_advance_zone_spawners(player_cell)
	if _runtime_registry.size() == 0:
		enemy_phase_finished.emit([])
		return []

	var results: Array = []
	for enemy_index in range(_runtime_registry.size()):
		var record = _runtime_registry.record_at(enemy_index)
		if record.is_dead:
			continue

		var result: Dictionary = await EnemyTurnSystemScript.take_enemy_turn(self, enemy_index, player_cell)
		results.append(result)

	_refresh_enemy_intents()
	enemy_phase_finished.emit(results)
	return results


func get_current_cell() -> Vector2i:
	for record in _runtime_registry.records:
		if record.occupies_cell():
			return record.current_cell
	return Vector2i.ZERO


func get_current_cells() -> Array[Vector2i]:
	return _runtime_registry.current_cells()


func set_cell_immediate(cell: Vector2i) -> void:
	if _runtime_registry.size() == 0:
		return
	var record = _runtime_registry.record_at(0)
	var enemy = record.enemy
	enemy.configure(_build_spawn_configuration(0), board_state)
	record.sync_from_enemy()
	record.restore_to_cell(cell, true)
	_refresh_enemy_intents()


func set_cells_immediate(cells: Array) -> void:
	for index in range(_runtime_registry.size()):
		var record = _runtime_registry.record_at(index)
		var enemy = record.enemy
		if index >= cells.size():
			record.restore_to_cell(record.current_cell, false)
			continue
		if index < board_state.enemy_spawns.size():
			enemy.configure(_build_spawn_configuration(index), board_state)
			record.sync_from_enemy()
		var cell: Vector2i = cells[index]
		record.restore_to_cell(cell, true)
	_refresh_enemy_intents()


func get_enemy_states() -> Dictionary:
	var enemy_states: Array[Dictionary] = []
	for record in _runtime_registry.records:
		enemy_states.append(record.build_state_snapshot())
	return {
		"enemies": enemy_states,
		"spawner_states": _zone_spawn_controller.build_state_snapshot(),
		"dynamic_spawn_order": _dynamic_spawn_order,
	}


func restore_enemy_states(enemy_states) -> void:
	var state_payload: Dictionary = {}
	var serialized_enemies: Array = []
	if enemy_states is Dictionary:
		state_payload = enemy_states
		serialized_enemies = state_payload.get("enemies", [])
		_zone_spawn_controller.restore_state_snapshot(state_payload.get("spawner_states", []))
		_dynamic_spawn_order = int(state_payload.get("dynamic_spawn_order", board_state.enemy_spawns.size()))
	else:
		serialized_enemies = enemy_states
		_zone_spawn_controller.setup(board_state)
		_dynamic_spawn_order = board_state.enemy_spawns.size()

	for child in get_children():
		child.free()
	_runtime_registry.clear()
	for enemy_state in serialized_enemies:
		if not enemy_state is Dictionary:
			continue
		var config: Dictionary = enemy_state.get("config", {})
		_spawn_enemy_from_data(config, int(config.get("spawn_order", 0)))
		_runtime_registry.record_at(_runtime_registry.size() - 1).restore_from_snapshot(enemy_state)
	_refresh_enemy_intents()


func any_enemy_at_cell(cell: Vector2i) -> bool:
	for record in _runtime_registry.records:
		if record.occupies_cell() and record.current_cell == cell:
			return true
	return false


func update_visibility(_visible_cells: Array[Vector2i]) -> void:
	for record in _runtime_registry.records:
		if record.enemy != null:
			record.enemy.visible = record.occupies_cell()
	_refresh_enemy_intents()


func get_spawn_warning_cells(player_cell: Vector2i) -> Array[Vector2i]:
	return _zone_spawn_controller.warning_cells(player_cell, get_current_cells())


func _build_blocked_lookup_for_mover(mover_index: int) -> Dictionary:
	return EnemyContactSystemScript.build_blocked_lookup(_runtime_registry, mover_index)


func _active_enemy_index_at_cell(cell: Vector2i, excluded_index: int) -> int:
	return EnemyContactSystemScript.active_enemy_index_at_cell(_runtime_registry, cell, excluded_index)


func _resolve_enemy_contact(mover_index: int, target_index: int) -> String:
	return EnemyContactSystemScript.resolve_contact(_runtime_registry.record_at(mover_index), _runtime_registry.record_at(target_index))

func _tint_for_spawn(spawn_data: Dictionary) -> Color:
	return EnemySchemaBridge.tint_for_spawn(spawn_data)


func _scene_for_spawn(spawn_data: Dictionary) -> PackedScene:
	match EnemySchemaBridge.scene_family_for_spawn(spawn_data):
		"chaser":
			return CHASER_SCENE
		"patroller":
			return PATROLLER_SCENE
		"stationary_blocker":
			return STATIONARY_BLOCKER_SCENE
		"wanderer":
			return WANDERER_SCENE
		"minotaur":
			return MINOTAUR_SCENE
		"samurai":
			return SAMURAI_SCENE
		_:
			return CHASER_SCENE


func _build_spawn_configuration(spawn_index: int) -> Dictionary:
	var spawn_data: Dictionary = board_state.enemy_spawns[spawn_index].duplicate(true)
	spawn_data["spawn_order"] = spawn_index
	spawn_data["tint"] = _tint_for_spawn(spawn_data)
	return spawn_data


func _spawn_enemy_from_data(spawn_data: Dictionary, spawn_order: int) -> void:
	var enemy_scene: PackedScene = _scene_for_spawn(spawn_data)
	var enemy = enemy_scene.instantiate()
	add_child(enemy)
	var configured_spawn := spawn_data.duplicate(true)
	configured_spawn["spawn_order"] = spawn_order
	configured_spawn["tint"] = _tint_for_spawn(configured_spawn)
	enemy.configure(configured_spawn, board_state)
	_runtime_registry.register_enemy(enemy)


func _refresh_enemy_intents() -> void:
	for enemy_index in range(_runtime_registry.size()):
		var record = _runtime_registry.record_at(enemy_index)
		if not record.occupies_cell():
			continue
		var enemy = record.enemy
		if enemy.has_method("refresh_intent_preview"):
			enemy.refresh_intent_preview(_build_blocked_lookup_for_mover(enemy_index))


func _advance_zone_spawners(player_cell: Vector2i) -> void:
	var occupied_cells := get_current_cells()
	for spawn_data in _zone_spawn_controller.advance(player_cell, occupied_cells):
		_spawn_enemy_from_data(spawn_data, _dynamic_spawn_order)
		_dynamic_spawn_order += 1
