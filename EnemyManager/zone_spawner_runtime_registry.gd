extends RefCounted
class_name ZoneSpawnerRuntimeRegistry

const ZoneSpawnerRuntimeRecordScript := preload("res://EnemyManager/zone_spawner_runtime_record.gd")

var records: Array = []


func clear() -> void:
	records.clear()


func register_spawner(spawner_config: Dictionary):
	var record = ZoneSpawnerRuntimeRecordScript.new().configure(spawner_config)
	records.append(record)
	return record


func record_at(index: int):
	return records[index]


func size() -> int:
	return records.size()
