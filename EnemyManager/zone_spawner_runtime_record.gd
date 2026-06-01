extends RefCounted
class_name ZoneSpawnerRuntimeRecord


var config: Dictionary = {}
var spawner_id: String = ""
var turns_until_spawn: int = 0


func configure(spawner_config: Dictionary) -> ZoneSpawnerRuntimeRecord:
	config = spawner_config.duplicate(true)
	spawner_id = String(config.get("id", ""))
	var interval: int = int(config.get("spawn_interval_turns", 2))
	turns_until_spawn = int(config.get("initial_delay_turns", interval))
	return self


func restore_from_snapshot(snapshot: Dictionary) -> ZoneSpawnerRuntimeRecord:
	if snapshot.has("config") and snapshot["config"] is Dictionary:
		config = snapshot.get("config", {}).duplicate(true)
		spawner_id = String(config.get("id", spawner_id))
	else:
		var merged: Dictionary = config.duplicate(true)
		merged.merge(snapshot, true)
		config = merged
		spawner_id = String(snapshot.get("id", spawner_id))
	turns_until_spawn = int(snapshot.get("turns_until_spawn", turns_until_spawn))
	return self


func build_state_snapshot() -> Dictionary:
	return {
		"config": config.duplicate(true),
		"id": spawner_id,
		"turns_until_spawn": turns_until_spawn,
	}
