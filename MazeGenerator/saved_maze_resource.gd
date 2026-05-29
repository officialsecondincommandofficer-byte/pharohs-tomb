extends Resource
class_name SavedMazeResource

const EnemySpawnDataScript = preload("res://MazeGenerator/enemy_spawn_data.gd")

@export var version: int = 1
@export var display_name: String = ""
@export var saved_at_unix: int = 0
@export var width: int = 0
@export var height: int = 0
@export var cell_size: int = 16
@export var size_category: String = "small"
@export var difficulty_category: String = "easy"
@export var horizontal_walls: Array[Vector2i] = []
@export var vertical_walls: Array[Vector2i] = []
@export var teleport_pairs: Array[Dictionary] = []
@export var enemy_teleport_pairs: Array[Dictionary] = []
@export var shared_teleport_pairs: Array[Dictionary] = []
@export var trap_cells: Array[Vector2i] = []
@export var player_spawn: Vector2i = Vector2i.ZERO
@export var enemy_spawns: Array[Dictionary] = []
@export var minotaur_spawn: Vector2i = Vector2i.ZERO
@export var exit_cell: Vector2i = Vector2i.ZERO
@export var solution_actions: Array[String] = []
@export var solution_total_steps: int = 0
@export var generation_mode: String = "RUNTIME_GENERATED"
@export var generation_profile_id: String = ""


func apply_payload(payload: Dictionary) -> void:
	version = int(payload.get("version", version))
	display_name = String(payload.get("display_name", display_name))
	saved_at_unix = int(payload.get("saved_at_unix", saved_at_unix))
	width = int(payload.get("width", width))
	height = int(payload.get("height", height))
	cell_size = int(payload.get("cell_size", cell_size))
	size_category = String(payload.get("size_category", size_category))
	difficulty_category = String(payload.get("difficulty_category", difficulty_category))
	horizontal_walls = _coerce_vector2i_array(payload.get("horizontal_walls", []))
	vertical_walls = _coerce_vector2i_array(payload.get("vertical_walls", []))
	teleport_pairs = _coerce_teleport_pair_array(payload.get("teleport_pairs", []))
	enemy_teleport_pairs = _coerce_teleport_pair_array(payload.get("enemy_teleport_pairs", []))
	shared_teleport_pairs = _coerce_teleport_pair_array(payload.get("shared_teleport_pairs", []))
	trap_cells = _coerce_vector2i_array(payload.get("trap_cells", []))
	player_spawn = _coerce_vector2i(payload.get("player_spawn", player_spawn))
	minotaur_spawn = _coerce_vector2i(payload.get("minotaur_spawn", minotaur_spawn))
	enemy_spawns = EnemySpawnDataScript.coerce_enemy_spawn_array(payload.get("enemy_spawns", []), minotaur_spawn, true)
	exit_cell = _coerce_vector2i(payload.get("exit_cell", exit_cell))
	solution_actions = _coerce_string_array(payload.get("solution_actions", []))
	solution_total_steps = int(payload.get("solution_total_steps", solution_total_steps))
	generation_mode = String(payload.get("generation_mode", generation_mode))
	generation_profile_id = String(payload.get("generation_profile_id", generation_profile_id))


func to_payload() -> Dictionary:
	return {
		"version": version,
		"display_name": display_name,
		"saved_at_unix": saved_at_unix,
		"width": width,
		"height": height,
		"cell_size": cell_size,
		"size_category": size_category,
		"difficulty_category": difficulty_category,
		"horizontal_walls": horizontal_walls.duplicate(),
		"vertical_walls": vertical_walls.duplicate(),
		"teleport_pairs": teleport_pairs.duplicate(true),
		"enemy_teleport_pairs": enemy_teleport_pairs.duplicate(true),
		"shared_teleport_pairs": shared_teleport_pairs.duplicate(true),
		"trap_cells": trap_cells.duplicate(),
		"player_spawn": player_spawn,
		"enemy_spawns": enemy_spawns.duplicate(true),
		"minotaur_spawn": minotaur_spawn,
		"exit_cell": exit_cell,
		"solution_actions": solution_actions.duplicate(),
		"solution_total_steps": solution_total_steps,
		"generation_mode": generation_mode,
		"generation_profile_id": generation_profile_id,
	}


func _coerce_vector2i(raw_value) -> Vector2i:
	if raw_value is Vector2i:
		return raw_value
	if raw_value is Vector2:
		return Vector2i(int(raw_value.x), int(raw_value.y))
	if raw_value is Array and raw_value.size() >= 2:
		return Vector2i(int(raw_value[0]), int(raw_value[1]))
	return Vector2i.ZERO


func _coerce_vector2i_array(raw_value) -> Array[Vector2i]:
	var coerced: Array[Vector2i] = []
	for entry in raw_value:
		coerced.append(_coerce_vector2i(entry))
	return coerced


func _coerce_teleport_pair_array(raw_value) -> Array[Dictionary]:
	var coerced: Array[Dictionary] = []
	for entry in raw_value:
		if not entry is Dictionary:
			continue
		coerced.append({
			"a": _coerce_vector2i(entry.get("a", Vector2i.ZERO)),
			"b": _coerce_vector2i(entry.get("b", Vector2i.ZERO)),
		})
	return coerced


func _coerce_string_array(raw_value) -> Array[String]:
	var coerced: Array[String] = []
	for entry in raw_value:
		coerced.append(String(entry))
	return coerced
