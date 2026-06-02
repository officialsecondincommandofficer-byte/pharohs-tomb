extends Node

@onready var scene_manager := SceneManager

func _ready() -> void:
	# Legacy bootstrap path kept for historical reference only.
	scene_manager.goto_scene("res://Legacy/Prototype/src/GameRunner/GameRunner.tscn")
