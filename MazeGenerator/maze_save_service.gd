extends RefCounted
class_name MazeSaveService

const SavedMazeResourceScript = preload("res://MazeGenerator/saved_maze_resource.gd")

const SAVE_DIRECTORY := "user://saved_mazes"


func save_board(board_state: MazeData) -> Dictionary:
	if board_state == null:
		return {
			"success": false,
			"error": ERR_INVALID_PARAMETER,
			"message": "There is no active maze to save.",
			"path": "",
			"file_name": "",
		}

	var saved_at_unix: int = Time.get_unix_time_from_system()
	var display_name := _build_display_name(board_state, saved_at_unix)
	var resource = SavedMazeResourceScript.new()
	resource.apply_payload(board_state.to_saved_payload(display_name, saved_at_unix))

	var directory_error: Error = DirAccess.make_dir_recursive_absolute(SAVE_DIRECTORY)
	if directory_error != OK:
		return {
			"success": false,
			"error": directory_error,
			"message": "Could not create the maze save folder.",
			"path": "",
			"file_name": "",
		}

	var file_name := _build_file_name(board_state, saved_at_unix)
	var save_path := "%s/%s" % [SAVE_DIRECTORY, file_name]
	var save_error: Error = ResourceSaver.save(resource, save_path)
	if save_error != OK:
		return {
			"success": false,
			"error": save_error,
			"message": "Could not save the current maze resource.",
			"path": save_path,
			"file_name": file_name,
		}

	return {
		"success": true,
		"error": OK,
		"message": "Maze saved.",
		"path": save_path,
		"file_name": file_name,
		"display_name": display_name,
	}


func _build_file_name(board_state: MazeData, saved_at_unix: int) -> String:
	var datetime := Time.get_datetime_dict_from_unix_time(saved_at_unix)
	return "%04d%02d%02d_%02d%02d%02d_%dx%d_%s.tres" % [
		int(datetime.get("year", 0)),
		int(datetime.get("month", 0)),
		int(datetime.get("day", 0)),
		int(datetime.get("hour", 0)),
		int(datetime.get("minute", 0)),
		int(datetime.get("second", 0)),
		board_state.width,
		board_state.height,
		board_state.difficulty_category.to_lower(),
	]


func _build_display_name(board_state: MazeData, saved_at_unix: int) -> String:
	var datetime := Time.get_datetime_dict_from_unix_time(saved_at_unix)
	return "%04d-%02d-%02d %02d:%02d:%02d %dx%d %s" % [
		int(datetime.get("year", 0)),
		int(datetime.get("month", 0)),
		int(datetime.get("day", 0)),
		int(datetime.get("hour", 0)),
		int(datetime.get("minute", 0)),
		int(datetime.get("second", 0)),
		board_state.width,
		board_state.height,
		board_state.difficulty_category.capitalize(),
	]
