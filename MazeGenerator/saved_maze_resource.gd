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
@export var player_horizontal_walls: Array[Vector2i] = []
@export var player_vertical_walls: Array[Vector2i] = []
@export var enemy_horizontal_walls: Array[Vector2i] = []
@export var enemy_vertical_walls: Array[Vector2i] = []
@export var one_way_passages: Array[Dictionary] = []
@export var teleport_pairs: Array[Dictionary] = []
@export var enemy_teleport_pairs: Array[Dictionary] = []
@export var shared_teleport_pairs: Array[Dictionary] = []
@export var trap_cells: Array[Vector2i] = []
@export var player_spawn: Vector2i = Vector2i.ZERO
@export var enemy_spawns: Array[Dictionary] = []
@export var minotaur_spawn: Vector2i = Vector2i.ZERO
@export var exit_cell: Vector2i = Vector2i.ZERO
@export var main_exit_cell: Vector2i = Vector2i.ZERO
@export var exit_cells: Array[Vector2i] = []
@export var main_exit_cells: Array[Vector2i] = []
@export var win_zone_cells: Array[Vector2i] = []
@export var escape_zone_cells: Array[Vector2i] = []
@export var zone_spawners: Array[Dictionary] = []
@export var escape_zone_spawners: Array[Dictionary] = []
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
	player_horizontal_walls = _coerce_vector2i_array(payload.get("player_horizontal_walls", []))
	player_vertical_walls = _coerce_vector2i_array(payload.get("player_vertical_walls", []))
	enemy_horizontal_walls = _coerce_vector2i_array(payload.get("enemy_horizontal_walls", []))
	enemy_vertical_walls = _coerce_vector2i_array(payload.get("enemy_vertical_walls", []))
	one_way_passages = _coerce_directed_edge_array(payload.get("one_way_passages", []))
	teleport_pairs = _coerce_teleport_pair_array(payload.get("teleport_pairs", []))
	enemy_teleport_pairs = _coerce_teleport_pair_array(payload.get("enemy_teleport_pairs", []))
	shared_teleport_pairs = _coerce_teleport_pair_array(payload.get("shared_teleport_pairs", []))
	trap_cells = _coerce_vector2i_array(payload.get("trap_cells", []))
	player_spawn = _coerce_vector2i(payload.get("player_spawn", player_spawn))
	minotaur_spawn = _coerce_vector2i(payload.get("minotaur_spawn", minotaur_spawn))
	enemy_spawns = EnemySpawnDataScript.coerce_enemy_spawn_array(payload.get("enemy_spawns", []), minotaur_spawn, true)
	main_exit_cell = _coerce_vector2i(payload.get("main_exit_cell", payload.get("exit_cell", main_exit_cell)))
	exit_cell = main_exit_cell
	main_exit_cells = _coerce_vector2i_array(payload.get("main_exit_cells", payload.get("exit_cells", [main_exit_cell])))
	if main_exit_cells.is_empty():
		main_exit_cells = [main_exit_cell]
	exit_cells = main_exit_cells.duplicate()
	escape_zone_cells = _coerce_vector2i_array(payload.get("escape_zone_cells", []))
	win_zone_cells = _coerce_vector2i_array(payload.get("win_zone_cells", _build_win_zone_cells(main_exit_cells, escape_zone_cells)))
	escape_zone_spawners = _coerce_dictionary_array(payload.get("escape_zone_spawners", payload.get("zone_spawners", [])))
	zone_spawners = escape_zone_spawners.duplicate(true)
	solution_actions = _coerce_string_array(payload.get("solution_actions", []))
	solution_total_steps = int(payload.get("solution_total_steps", solution_total_steps))
	generation_mode = String(payload.get("generation_mode", generation_mode))
	generation_profile_id = String(payload.get("generation_profile_id", generation_profile_id))


func to_payload() -> Dictionary:
	var resolved_main_exit_cell := main_exit_cell if main_exit_cell != Vector2i.ZERO else exit_cell
	var resolved_main_exit_cells := main_exit_cells.duplicate() if not main_exit_cells.is_empty() else exit_cells.duplicate()
	if resolved_main_exit_cells.is_empty():
		resolved_main_exit_cells = [resolved_main_exit_cell]
	var resolved_escape_zone_spawners := escape_zone_spawners.duplicate(true) if not escape_zone_spawners.is_empty() else zone_spawners.duplicate(true)
	var resolved_win_zone_cells := win_zone_cells.duplicate() if not win_zone_cells.is_empty() else _build_win_zone_cells(resolved_main_exit_cells, escape_zone_cells)

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
		"player_horizontal_walls": player_horizontal_walls.duplicate(),
		"player_vertical_walls": player_vertical_walls.duplicate(),
		"enemy_horizontal_walls": enemy_horizontal_walls.duplicate(),
		"enemy_vertical_walls": enemy_vertical_walls.duplicate(),
		"one_way_passages": one_way_passages.duplicate(true),
		"teleport_pairs": teleport_pairs.duplicate(true),
		"enemy_teleport_pairs": enemy_teleport_pairs.duplicate(true),
		"shared_teleport_pairs": shared_teleport_pairs.duplicate(true),
		"trap_cells": trap_cells.duplicate(),
		"player_spawn": player_spawn,
		"enemy_spawns": enemy_spawns.duplicate(true),
		"minotaur_spawn": minotaur_spawn,
		"exit_cell": exit_cell,
		"main_exit_cell": resolved_main_exit_cell,
		"exit_cells": exit_cells.duplicate() if not exit_cells.is_empty() else [exit_cell],
		"main_exit_cells": resolved_main_exit_cells,
		"win_zone_cells": resolved_win_zone_cells,
		"escape_zone_cells": escape_zone_cells.duplicate(),
		"zone_spawners": zone_spawners.duplicate(true),
		"escape_zone_spawners": resolved_escape_zone_spawners,
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


func _coerce_directed_edge_array(raw_value) -> Array[Dictionary]:
	var coerced: Array[Dictionary] = []
	for entry in raw_value:
		if not entry is Dictionary:
			continue
		coerced.append({
			"from": _coerce_vector2i(entry.get("from", Vector2i.ZERO)),
			"to": _coerce_vector2i(entry.get("to", Vector2i.ZERO)),
		})
	return coerced


func _coerce_string_array(raw_value) -> Array[String]:
	var coerced: Array[String] = []
	for entry in raw_value:
		coerced.append(String(entry))
	return coerced


func _coerce_dictionary_array(raw_value) -> Array[Dictionary]:
	var coerced: Array[Dictionary] = []
	for entry in raw_value:
		if entry is Dictionary:
			coerced.append(entry.duplicate(true))
	return coerced


func _build_win_zone_cells(next_main_exit_cells: Array[Vector2i], next_escape_zone_cells: Array[Vector2i]) -> Array[Vector2i]:
	var cells := next_main_exit_cells.duplicate()
	for escape_zone_cell in next_escape_zone_cells:
		if not cells.has(escape_zone_cell):
			cells.append(escape_zone_cell)
	return cells
