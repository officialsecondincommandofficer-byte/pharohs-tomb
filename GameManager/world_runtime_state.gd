extends RefCounted
class_name WorldRuntimeState

const PlayerRuntimeStateScript := preload("res://Player/player_runtime_state.gd")
const WorldEnemyPhaseRuntimePayloadScript := preload("res://GameManager/world_enemy_phase_runtime_payload.gd")
const WorldBoardEffectRuntimePayloadScript := preload("res://GameManager/world_board_effect_runtime_payload.gd")

var player_state = PlayerRuntimeStateScript.new()
var enemy_phase_runtime_payload = WorldEnemyPhaseRuntimePayloadScript.new()
var board_effect_runtime_payload = WorldBoardEffectRuntimePayloadScript.new()
var move_count: int = 0
var game_over: bool = false


func capture_from_runtime(player, enemy_manager, next_move_count: int = 0, next_game_over: bool = false):
	if player != null and player.has_method("build_state_snapshot"):
		player_state.restore_from_snapshot(player.build_state_snapshot())
	if enemy_manager != null and enemy_manager.has_method("export_runtime_payload"):
		enemy_phase_runtime_payload = _enemy_phase_payload_from_runtime(enemy_manager.export_runtime_payload())
	elif enemy_manager != null and enemy_manager.has_method("get_enemy_states"):
		enemy_phase_runtime_payload = _enemy_phase_payload_from_runtime(enemy_manager.get_enemy_states())
	board_effect_runtime_payload = WorldBoardEffectRuntimePayloadScript.new()
	move_count = next_move_count
	game_over = next_game_over
	return self


func apply_to_runtime(player, enemy_manager) -> void:
	player_state.apply_to_player(player)
	if enemy_manager != null and enemy_manager.has_method("restore_runtime_payload"):
		enemy_manager.restore_runtime_payload(enemy_phase_runtime_payload)
	elif enemy_manager != null and enemy_manager.has_method("restore_enemy_states"):
		enemy_manager.restore_enemy_states(enemy_phase_runtime_payload.to_dictionary())


func build_snapshot(action_name: String = "") -> Dictionary:
	var serialized_enemy_payload: Dictionary = enemy_phase_runtime_payload.to_dictionary()
	var serialized_board_effect_payload: Dictionary = board_effect_runtime_payload.to_dictionary()
	var snapshot := {
		"action": action_name,
		"player": player_state.current_cell,
		"player_state": player_state.build_state_snapshot(),
		"enemy_runtime_payload": serialized_enemy_payload,
		"enemy_states": serialized_enemy_payload.duplicate(true),
		"board_effect_runtime_payload": serialized_board_effect_payload,
		"move_count": move_count,
		"game_over": game_over,
	}
	snapshot["enemies"] = _enemy_cells_from_payload()
	snapshot["minotaur"] = _first_enemy_cell(snapshot["enemies"])
	return snapshot


func restore_from_snapshot(snapshot: Dictionary) -> void:
	var legacy_player_state := {
		"cell": snapshot.get("player", player_state.current_cell),
		"alive": not bool(snapshot.get("game_over", false)),
	}
	player_state.restore_from_snapshot(snapshot.get("player_state", legacy_player_state))
	if snapshot.has("enemy_runtime_payload"):
		enemy_phase_runtime_payload = _enemy_phase_payload_from_runtime(
			snapshot.get("enemy_runtime_payload", enemy_phase_runtime_payload)
		)
	elif snapshot.has("enemy_states"):
		enemy_phase_runtime_payload = _enemy_phase_payload_from_runtime(
			snapshot.get("enemy_states", enemy_phase_runtime_payload)
		)
	else:
		enemy_phase_runtime_payload = WorldEnemyPhaseRuntimePayloadScript.legacy_from_snapshot(snapshot)
	board_effect_runtime_payload = _board_effect_payload_from_runtime(
		snapshot.get("board_effect_runtime_payload", board_effect_runtime_payload)
	)
	move_count = int(snapshot.get("move_count", move_count))
	game_over = bool(snapshot.get("game_over", game_over))


func duplicate_state():
	var duplicate = get_script().new()
	duplicate.player_state = player_state.duplicate_state()
	duplicate.enemy_phase_runtime_payload = enemy_phase_runtime_payload.duplicate_payload()
	duplicate.board_effect_runtime_payload = board_effect_runtime_payload.duplicate_payload()
	duplicate.move_count = move_count
	duplicate.game_over = game_over
	return duplicate


func _enemy_phase_payload_from_runtime(runtime_payload):
	if runtime_payload != null and runtime_payload is RefCounted and runtime_payload.get_script() == WorldEnemyPhaseRuntimePayloadScript:
		return runtime_payload.duplicate_payload()
	if runtime_payload is Dictionary:
		return WorldEnemyPhaseRuntimePayloadScript.new().from_dictionary(runtime_payload)
	return WorldEnemyPhaseRuntimePayloadScript.new()


func _board_effect_payload_from_runtime(runtime_payload):
	if runtime_payload != null and runtime_payload is RefCounted and runtime_payload.get_script() == WorldBoardEffectRuntimePayloadScript:
		return runtime_payload.duplicate_payload()
	if runtime_payload is Dictionary:
		return WorldBoardEffectRuntimePayloadScript.new().from_dictionary(runtime_payload)
	return WorldBoardEffectRuntimePayloadScript.new()


func _enemy_cells_from_payload() -> Array[Vector2i]:
	return enemy_phase_runtime_payload.alive_enemy_cells()


static func _first_enemy_cell(enemy_cells: Array[Vector2i]) -> Vector2i:
	if enemy_cells.is_empty():
		return Vector2i.ZERO
	return enemy_cells[0]
