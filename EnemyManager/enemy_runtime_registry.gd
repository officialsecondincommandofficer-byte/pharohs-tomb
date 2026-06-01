extends RefCounted
class_name EnemyRuntimeRegistry

const EnemyRuntimeRecordScript := preload("res://EnemyManager/enemy_runtime_record.gd")

var records: Array = []


func clear() -> void:
	records.clear()


func register_enemy(enemy):
	var record = EnemyRuntimeRecordScript.new().bind_enemy(enemy)
	records.append(record)
	return record


func record_at(index: int):
	return records[index]


func size() -> int:
	return records.size()


func active_record_index_at_cell(cell: Vector2i, excluded_index: int) -> int:
	for index in range(records.size()):
		if index == excluded_index:
			continue
		var record = records[index]
		if not record.occupies_cell():
			continue
		if record.current_cell == cell:
			return index
	return -1


func current_cells() -> Array[Vector2i]:
	var cells: Array[Vector2i] = []
	for record in records:
		if record.occupies_cell():
			cells.append(record.current_cell)
	return cells
