extends "res://EnemyManager/enemy_base.gd"

const EnemyBehaviorSystemsScript := preload("res://EnemyManager/enemy_behavior_systems.gd")
const ROTATION_DIRECTIONS: Array[Vector2i] = [
	Vector2i.UP,
	Vector2i.RIGHT,
	Vector2i.DOWN,
	Vector2i.LEFT,
]

var facing_index: int = 2
var decision_count: int = 0
var visit_tick: int = 0
var visited_ticks: Dictionary = {}
var _intent_direction := Vector2i.ZERO


func _ready() -> void:
	enemy_type = "wanderer"
	super._ready()


func configure(spawn_data: Dictionary, next_board_state) -> void:
	super.configure(spawn_data, next_board_state)
	facing_index = posmod(runtime_config.facing_index, ROTATION_DIRECTIONS.size())
	decision_count = 0
	visit_tick = 0
	visited_ticks.clear()
	_intent_direction = Vector2i.ZERO
	queue_redraw()

func refresh_intent_preview(occupied_lookup: Dictionary) -> void:
	var plan: Dictionary = EnemyBehaviorSystemsScript.choose_wanderer_plan(
		current_cell,
		facing_index,
		behavior_seed,
		decision_count,
		visited_ticks,
		occupied_lookup,
		func(direction_index: int, occupied: Dictionary) -> bool:
			var target_cell: Vector2i = current_cell + ROTATION_DIRECTIONS[direction_index]
			return _can_enter(target_cell, occupied)
	)
	var next_cell: Vector2i = plan.get("cell", current_cell)
	_intent_direction = next_cell - current_cell
	queue_redraw()


func build_spawn_snapshot() -> Dictionary:
	var snapshot := super.build_spawn_snapshot()
	snapshot["facing_index"] = facing_index
	return snapshot


func _build_behavior_state_snapshot() -> Dictionary:
	return {
		"facing_index": facing_index,
		"decision_count": decision_count,
		"visit_tick": visit_tick,
		"visited_ticks": _build_visited_ticks_snapshot(),
	}


func _restore_behavior_state_snapshot(state: Dictionary) -> void:
	facing_index = posmod(int(state.get("facing_index", facing_index)), ROTATION_DIRECTIONS.size())
	decision_count = int(state.get("decision_count", decision_count))
	visit_tick = int(state.get("visit_tick", visit_tick))
	visited_ticks.clear()
	for entry in state.get("visited_ticks", []):
		if not entry is Dictionary:
			continue
		var cell := _coerce_vector2i(entry.get("cell", Vector2i.ZERO))
		visited_ticks[cell] = int(entry.get("tick", 0))
	queue_redraw()


func _draw() -> void:
	if _intent_direction == Vector2i.ZERO:
		return
	var direction := Vector2(_intent_direction.x, _intent_direction.y).normalized()
	var line_end := direction * 11.0
	draw_line(Vector2.ZERO, line_end, Color(1.0, 0.95, 0.35, 0.95), 2.0)
	var tip := line_end
	var left := tip - direction * 3.0 + Vector2(-direction.y, direction.x) * 2.0
	var right := tip - direction * 3.0 + Vector2(direction.y, -direction.x) * 2.0
	draw_colored_polygon(PackedVector2Array([tip, left, right]), Color(1.0, 0.95, 0.35, 0.95))

func _build_visited_ticks_snapshot() -> Array[Dictionary]:
	var entries: Array[Dictionary] = []
	for cell in visited_ticks.keys():
		entries.append({
			"cell": cell,
			"tick": int(visited_ticks[cell]),
		})
	entries.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		var cell_a: Vector2i = a.get("cell", Vector2i.ZERO)
		var cell_b: Vector2i = b.get("cell", Vector2i.ZERO)
		if cell_a.y == cell_b.y:
			return cell_a.x < cell_b.x
		return cell_a.y < cell_b.y
	)
	return entries
