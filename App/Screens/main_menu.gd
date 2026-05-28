extends Control

signal play_requested
signal quit_requested

@onready var play_button: Button = $CenterContainer/PanelContainer/MarginContainer/VBoxContainer/PlayButton
@onready var quit_button: Button = $CenterContainer/PanelContainer/MarginContainer/VBoxContainer/QuitButton


func _ready() -> void:
	play_button.pressed.connect(_on_play_pressed)
	quit_button.pressed.connect(_on_quit_pressed)


func _on_play_pressed() -> void:
	play_requested.emit()


func _on_quit_pressed() -> void:
	quit_requested.emit()
