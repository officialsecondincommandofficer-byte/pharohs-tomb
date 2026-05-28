extends RefCounted
class_name WorldCatalogService

const WORLDS_ROOT := "res://Resources/Worlds"
const WorldManifestParserScript = preload("res://Worlds/world_manifest_parser.gd")

var _manifest_parser


func _init() -> void:
	_manifest_parser = WorldManifestParserScript.new()


func load_worlds(root_path: String = WORLDS_ROOT) -> Array:
	var worlds: Array = []
	var root_directory := DirAccess.open(root_path)
	if root_directory == null:
		push_warning("WorldCatalogService could not open worlds root: %s" % root_path)
		return worlds

	var directory_names: Array[String] = []
	root_directory.list_dir_begin()
	while true:
		var entry := root_directory.get_next()
		if entry.is_empty():
			break
		if entry == "." or entry == "..":
			continue
		if root_directory.current_is_dir():
			directory_names.append(entry)
	root_directory.list_dir_end()

	directory_names.sort()
	for directory_name in directory_names:
		var world_directory := root_path.path_join(directory_name)
		var manifest_path := _find_manifest_path(world_directory)
		if manifest_path.is_empty():
			continue
		var world_definition = _manifest_parser.parse_manifest(manifest_path)
		if world_definition == null or world_definition.levels.is_empty():
			continue
		worlds.append(world_definition)

	return worlds


func _find_manifest_path(world_directory: String) -> String:
	var canonical_manifest := world_directory.path_join("world_manifest.json")
	if FileAccess.file_exists(canonical_manifest):
		return canonical_manifest

	var directory := DirAccess.open(world_directory)
	if directory == null:
		return ""

	var latest_export_manifest := ""
	var latest_modified_time := -1
	var fallback_manifest := ""

	directory.list_dir_begin()
	while true:
		var entry := directory.get_next()
		if entry.is_empty():
			break
		if entry == "." or entry == ".." or directory.current_is_dir():
			continue
		if not entry.ends_with(".json"):
			continue

		var entry_path := world_directory.path_join(entry)
		if fallback_manifest.is_empty():
			fallback_manifest = entry_path
		if entry.begins_with("minotaur_export_manifest_"):
			var modified_time := FileAccess.get_modified_time(entry_path)
			if modified_time > latest_modified_time:
				latest_modified_time = modified_time
				latest_export_manifest = entry_path
	directory.list_dir_end()

	if not latest_export_manifest.is_empty():
		return latest_export_manifest
	return fallback_manifest
