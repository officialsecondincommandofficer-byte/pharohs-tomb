extends RefCounted
class_name WorldRuntimeRegistry

const WorldRuntimeStateScript := preload("res://GameManager/world_runtime_state.gd")

var current_state = WorldRuntimeStateScript.new()
var _start_snapshot: Dictionary = {}
var _history: Array[Dictionary] = []


func capture_from_runtime(player, enemy_manager, move_count: int = 0, game_over: bool = false) -> WorldRuntimeRegistry:
	current_state = WorldRuntimeStateScript.new().capture_from_runtime(player, enemy_manager, move_count, game_over)
	return self


func cache_start_snapshot() -> Dictionary:
	_start_snapshot = current_state.build_snapshot("start").duplicate(true)
	_history.clear()
	_history.append(_start_snapshot.duplicate(true))
	return _start_snapshot.duplicate(true)


func restore_start_snapshot(player, enemy_manager) -> bool:
	if _start_snapshot.is_empty():
		return false
	restore_snapshot(_start_snapshot, player, enemy_manager)
	_history.clear()
	_history.append(_start_snapshot.duplicate(true))
	return true


func restore_snapshot(snapshot: Dictionary, player, enemy_manager) -> Dictionary:
	current_state = WorldRuntimeStateScript.new()
	current_state.restore_from_snapshot(snapshot)
	current_state.apply_to_runtime(player, enemy_manager)
	return current_state.build_snapshot(String(snapshot.get("action", "")))


func apply_to_runtime(player, enemy_manager) -> void:
	current_state.apply_to_runtime(player, enemy_manager)


func duplicate_runtime_state():
	return current_state.duplicate_state()


func commit_runtime_state(next_state, action_name: String) -> Dictionary:
	current_state = next_state.duplicate_state()
	var snapshot: Dictionary = current_state.build_snapshot(action_name)
	_history.append(snapshot.duplicate(true))
	return snapshot


func current_snapshot(action_name: String = "") -> Dictionary:
	return current_state.build_snapshot(action_name)


func undo(player, enemy_manager) -> Dictionary:
	if _history.size() <= 1:
		return {}
	_history.pop_back()
	var snapshot: Dictionary = _history.back().duplicate(true)
	restore_snapshot(snapshot, player, enemy_manager)
	return snapshot


func can_undo() -> bool:
	return _history.size() > 1


func history_size() -> int:
	return _history.size()


func has_start_snapshot() -> bool:
	return not _start_snapshot.is_empty()


func move_count() -> int:
	return current_state.move_count


func is_game_over() -> bool:
	return current_state.game_over


func player_cell() -> Vector2i:
	return current_state.player_state.current_cell
