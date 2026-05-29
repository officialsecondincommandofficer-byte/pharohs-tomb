extends RefCounted
class_name LevelBoardLoader

const MazeDataScript = preload("res://MazeGenerator/maze_data.gd")


func load_level(level_definition) -> MazeData:
	if level_definition == null or level_definition.resource_path.is_empty():
		return null

	var saved_resource := load(level_definition.resource_path)
	var board_state: MazeData = MazeDataScript.from_saved_resource(saved_resource)
	if board_state == null:
		push_warning("LevelBoardLoader could not load board resource: %s" % level_definition.resource_path)
		return null

	board_state.display_name = level_definition.display_name
	board_state.generation_mode = "WORLD_LEVEL"
	board_state.generation_profile_id = level_definition.level_id
	if level_definition.solution_total_steps > 0:
		board_state.solution_total_steps = level_definition.solution_total_steps
	if not level_definition.difficulty.is_empty():
		board_state.difficulty_category = level_definition.difficulty
	return board_state
