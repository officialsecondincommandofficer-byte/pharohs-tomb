extends RefCounted
class_name WorldManifestParser

const WorldDefinitionScript = preload("res://Worlds/world_definition.gd")
const WorldLevelDefinitionScript = preload("res://Worlds/world_level_definition.gd")


func parse_manifest(manifest_path: String):
	var file := FileAccess.open(manifest_path, FileAccess.READ)
	if file == null:
		push_warning("WorldManifestParser could not open manifest: %s" % manifest_path)
		return null

	var parsed_manifest = JSON.parse_string(file.get_as_text())
	if not parsed_manifest is Dictionary:
		push_warning("WorldManifestParser expected a dictionary manifest: %s" % manifest_path)
		return null

	return _parse_manifest_dictionary(manifest_path, manifest_path.get_base_dir(), parsed_manifest)


func _parse_manifest_dictionary(manifest_path: String, world_directory: String, manifest: Dictionary):
	if manifest.has("levels") or manifest.has("imports"):
		return _parse_world_manifest(manifest_path, world_directory, manifest)
	if manifest.has("files"):
		return _parse_export_manifest(manifest_path, world_directory, manifest)

	push_warning("WorldManifestParser found an unsupported manifest format: %s" % manifest_path)
	return null


func _parse_world_manifest(
	manifest_path: String,
	world_directory: String,
	manifest: Dictionary
):
	var world_id := String(manifest.get("id", world_directory.get_file().to_lower()))
	var levels := _collect_world_levels(world_directory, manifest, world_id)
	if levels.is_empty():
		return null

	return WorldDefinitionScript.new().configure({
		"world_id": world_id,
		"display_name": String(manifest.get("display_name", _humanize_slug(world_directory.get_file()))),
		"description": String(manifest.get("description", "")),
		"manifest_path": manifest_path,
		"world_directory": world_directory,
		"source_type": "world_manifest",
		"levels": levels,
	})


func _parse_export_manifest(
	manifest_path: String,
	world_directory: String,
	manifest: Dictionary
):
	var levels: Array = []
	var raw_files = manifest.get("files", [])
	if not raw_files is Array:
		return null

	var world_id := world_directory.get_file().to_lower()
	for index in raw_files.size():
		var raw_file = raw_files[index]
		if not raw_file is Dictionary:
			continue
		var resource_path := _resolve_export_resource_path(world_directory, raw_file)
		if resource_path.is_empty():
			continue
		levels.append(
			WorldLevelDefinitionScript.new().configure({
				"level_id": "%s_%02d" % [world_id, index + 1],
				"display_name": _humanize_file_name(String(raw_file.get("file_name", resource_path.get_file()))),
				"resource_path": resource_path,
				"width": int(raw_file.get("width", 0)),
				"height": int(raw_file.get("height", 0)),
				"difficulty": String(raw_file.get("difficulty_category", "")),
				"solution_total_steps": int(raw_file.get("solution_total_steps", 0)),
				"order_index": index,
			})
		)

	var width := int(manifest.get("parameters", {}).get("width", 0))
	var height := int(manifest.get("parameters", {}).get("height", 0))
	var description := "Imported export manifest"
	if width > 0 and height > 0:
		description = "Imported export manifest for %dx%d boards." % [width, height]

	return WorldDefinitionScript.new().configure({
		"world_id": world_id,
		"display_name": _humanize_slug(world_directory.get_file()),
		"description": description,
		"manifest_path": manifest_path,
		"world_directory": world_directory,
		"source_type": "export_manifest",
		"levels": levels,
	})


func _collect_world_levels(world_directory: String, manifest: Dictionary, world_id: String) -> Array:
	var levels: Array = []
	var next_order_index := 0
	var raw_levels = manifest.get("levels", [])
	if raw_levels is Array:
		for level_entry in raw_levels:
			if not level_entry is Dictionary:
				continue
			var level_definition = _build_level_definition_from_entry(
				world_directory,
				world_id,
				level_entry,
				next_order_index
			)
			if level_definition == null:
				continue
			levels.append(level_definition)
			next_order_index += 1

	var imports = manifest.get("imports", [])
	if imports is Array:
		for import_entry in imports:
			var imported_levels := _load_imported_levels(
				world_directory,
				world_id,
				import_entry,
				next_order_index
			)
			for imported_level in imported_levels:
				levels.append(imported_level)
				next_order_index += 1

	return levels


func _build_level_definition_from_entry(
	world_directory: String,
	world_id: String,
	level_entry: Dictionary,
	order_index: int
):
	var resource_path := _resolve_resource_path(
		world_directory,
		String(level_entry.get("resource", level_entry.get("path", "")))
	)
	if resource_path.is_empty():
		return null

	return WorldLevelDefinitionScript.new().configure({
		"level_id": String(level_entry.get("id", "%s_%02d" % [world_id, order_index + 1])),
		"display_name": String(level_entry.get("display_name", _humanize_file_name(resource_path.get_file()))),
		"resource_path": resource_path,
		"width": int(level_entry.get("width", 0)),
		"height": int(level_entry.get("height", 0)),
		"difficulty": String(level_entry.get("difficulty", "")),
		"solution_total_steps": int(level_entry.get("solution_total_steps", 0)),
		"order_index": order_index,
	})


func _load_imported_levels(
	world_directory: String,
	world_id: String,
	import_entry,
	start_order_index: int
) -> Array:
	var import_path := ""
	var display_name_prefix := ""
	var id_prefix := ""
	if import_entry is String:
		import_path = _resolve_resource_path(world_directory, import_entry)
	elif import_entry is Dictionary:
		import_path = _resolve_resource_path(world_directory, String(import_entry.get("path", "")))
		display_name_prefix = String(import_entry.get("display_name_prefix", ""))
		id_prefix = String(import_entry.get("id_prefix", ""))
	else:
		return []

	if import_path.is_empty():
		return []

	var file := FileAccess.open(import_path, FileAccess.READ)
	if file == null:
		push_warning("WorldManifestParser could not open imported manifest: %s" % import_path)
		return []

	var parsed_manifest = JSON.parse_string(file.get_as_text())
	if not parsed_manifest is Dictionary:
		push_warning("WorldManifestParser expected a dictionary import: %s" % import_path)
		return []

	var imported_world = _parse_manifest_dictionary(import_path, import_path.get_base_dir(), parsed_manifest)
	if imported_world == null:
		return []

	var remapped_levels: Array = []
	for imported_index in imported_world.levels.size():
		var imported_level = imported_world.levels[imported_index]
		var display_name = imported_level.display_name
		if not display_name_prefix.is_empty():
			display_name = "%s %s" % [display_name_prefix, display_name]

		var level_id = imported_level.level_id
		if not id_prefix.is_empty():
			level_id = "%s_%s" % [id_prefix, imported_level.level_id]
		else:
			level_id = "%s_%s_%02d" % [world_id, imported_world.world_id, imported_index + 1]

		remapped_levels.append(
			WorldLevelDefinitionScript.new().configure({
				"level_id": level_id,
				"display_name": display_name,
				"resource_path": imported_level.resource_path,
				"width": imported_level.width,
				"height": imported_level.height,
				"difficulty": imported_level.difficulty,
				"solution_total_steps": imported_level.solution_total_steps,
				"order_index": start_order_index + imported_index,
			})
		)

	return remapped_levels


func _resolve_export_resource_path(world_directory: String, file_entry: Dictionary) -> String:
	var local_file_name := String(file_entry.get("file_name", ""))
	if not local_file_name.is_empty():
		var local_path := world_directory.path_join(local_file_name)
		if FileAccess.file_exists(local_path):
			return local_path

	return _resolve_resource_path(world_directory, String(file_entry.get("path", local_file_name)))


func _resolve_resource_path(world_directory: String, raw_path: String) -> String:
	if raw_path.is_empty():
		return ""
	if raw_path.begins_with("res://"):
		return raw_path

	var normalized_path := raw_path.replace("\\", "/")
	if normalized_path.contains("/"):
		var workspace_segment := "/pharohs-tomb/"
		var workspace_index := normalized_path.find(workspace_segment)
		if workspace_index != -1:
			return "res://%s" % normalized_path.substr(workspace_index + workspace_segment.length())

		var resources_index := normalized_path.find("/Resources/")
		if resources_index != -1:
			return "res://%s" % normalized_path.substr(resources_index + 1)

	var relative_path := raw_path
	if raw_path.contains("/") or raw_path.contains("\\"):
		relative_path = normalized_path
	return world_directory.path_join(relative_path)


func _humanize_slug(slug: String) -> String:
	return slug.replace("_", " ").replace("-", " ").capitalize()


func _humanize_file_name(file_name: String) -> String:
	return _humanize_slug(file_name.get_basename())
