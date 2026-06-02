extends Control

const MainMenuScene = preload("res://App/Screens/MainMenu.tscn")
const WorldSelectScene = preload("res://App/Screens/WorldSelectScreen.tscn")
const LevelSelectScene = preload("res://App/Screens/LevelSelectScreen.tscn")
const GameplayScreenScene = preload("res://Gameplay/GameplayScreen.tscn")
const WorldCatalogServiceScript = preload("res://Worlds/world_catalog_service.gd")

@onready var content_root: Control = $ContentRoot
@onready var loading_screen: CanvasLayer = $LoadingScreen

var _active_screen: Node = null
var _world_catalog_service
var _worlds: Array = []
var _selected_world = null
var _selected_level_index: int = -1


func _ready() -> void:
	_world_catalog_service = WorldCatalogServiceScript.new()
	_reload_worlds()
	_show_main_menu()


func _reload_worlds() -> void:
	_worlds = _world_catalog_service.load_worlds()


func _show_main_menu() -> void:
	var screen = MainMenuScene.instantiate()
	screen.play_requested.connect(_on_play_requested)
	screen.quit_requested.connect(_on_quit_requested)
	_swap_screen(screen, "Waking the tomb...", "Preparing the main menu.")


func _show_world_select() -> void:
	_reload_worlds()
	var screen = WorldSelectScene.instantiate()
	screen.configure_worlds(_worlds)
	screen.world_confirmed.connect(_on_world_confirmed)
	screen.back_requested.connect(_show_main_menu)
	_swap_screen(screen, "Surveying the tomb...", "Gathering the available worlds.")


func _show_level_select(world_definition) -> void:
	_selected_world = world_definition
	var screen = LevelSelectScene.instantiate()
	screen.configure_world(world_definition)
	screen.level_confirmed.connect(_on_level_confirmed)
	screen.back_requested.connect(_show_world_select)
	_swap_screen(
		screen,
		"Charting a route...",
		"Loading the level list for %s." % world_definition.display_name
	)


func _start_level(level_definition) -> void:
	if _selected_world == null or level_definition == null:
		return

	_selected_level_index = _find_level_index(level_definition)
	var gameplay = GameplayScreenScene.instantiate()
	gameplay.configure_selected_level(_selected_world, level_definition)
	gameplay.return_to_level_select_requested.connect(_on_return_to_level_select_requested)
	gameplay.next_level_requested.connect(_on_next_level_requested)
	_swap_screen(
		gameplay,
		"Descending...",
		"Entering %s." % level_definition.display_name
	)


func _swap_screen(next_screen: Node, title: String, detail: String) -> void:
	loading_screen.show_loading_screen(title, detail)
	if _active_screen != null:
		_active_screen.queue_free()
	_active_screen = next_screen
	content_root.add_child(next_screen)
	loading_screen.hide_immediately()


func _on_play_requested() -> void:
	_show_world_select()


func _on_quit_requested() -> void:
	get_tree().quit()


func _on_world_confirmed(world_definition) -> void:
	_show_level_select(world_definition)


func _on_level_confirmed(level_definition) -> void:
	_start_level(level_definition)


func _on_return_to_level_select_requested() -> void:
	if _selected_world == null:
		_show_world_select()
		return
	_show_level_select(_selected_world)


func _on_next_level_requested() -> void:
	if _selected_world == null:
		_show_world_select()
		return

	var next_index := _selected_level_index + 1
	if next_index < 0 or next_index >= _selected_world.levels.size():
		_selected_level_index = -1
		_show_world_select()
		return

	_start_level(_selected_world.levels[next_index])


func _find_level_index(level_definition) -> int:
	if _selected_world == null or level_definition == null:
		return -1

	for index in _selected_world.levels.size():
		if _selected_world.levels[index].level_id == level_definition.level_id:
			return index
	return -1
