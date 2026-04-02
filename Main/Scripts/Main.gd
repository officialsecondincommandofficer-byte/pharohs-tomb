extends Node

@onready var scene_manager := SceneManager

func _ready() -> void:
	# Load the starting scene when the game launches
	scene_manager.goto_scene("res://src/GameRunner/GameRunner.tscn")
