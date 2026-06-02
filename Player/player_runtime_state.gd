extends RefCounted
class_name PlayerRuntimeState


var current_cell: Vector2i = Vector2i.ZERO
var is_alive: bool = true


func configure(cell: Vector2i, alive: bool = true) -> PlayerRuntimeState:
	current_cell = cell
	is_alive = alive
	return self


func move_to_cell(cell: Vector2i) -> void:
	current_cell = cell


func restore_to_cell(cell: Vector2i, alive: bool) -> void:
	current_cell = cell
	is_alive = alive


func mark_dead() -> void:
	is_alive = false


func build_state_snapshot() -> Dictionary:
	return {
		"cell": current_cell,
		"alive": is_alive,
	}


func restore_from_snapshot(snapshot: Dictionary) -> void:
	current_cell = snapshot.get("cell", current_cell)
	is_alive = bool(snapshot.get("alive", is_alive))


func duplicate_state() -> PlayerRuntimeState:
	return get_script().new().configure(current_cell, is_alive)


func apply_to_player(player) -> void:
	if player == null:
		return
	player.restore_from_state(build_state_snapshot())
