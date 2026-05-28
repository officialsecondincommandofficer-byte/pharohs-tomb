extends RefCounted
class_name WorldDefinition

var world_id: String = ""
var display_name: String = ""
var description: String = ""
var manifest_path: String = ""
var world_directory: String = ""
var source_type: String = "world_manifest"
var levels: Array = []


func configure(data: Dictionary) -> WorldDefinition:
	world_id = String(data.get("world_id", ""))
	display_name = String(data.get("display_name", ""))
	description = String(data.get("description", ""))
	manifest_path = String(data.get("manifest_path", ""))
	world_directory = String(data.get("world_directory", ""))
	source_type = String(data.get("source_type", source_type))
	levels = data.get("levels", [])
	return self


func level_count() -> int:
	return levels.size()
