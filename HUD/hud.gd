extends CanvasLayer

@onready var board_label: Label = $PanelContainer/MarginContainer/VBoxContainer/FloorLabel
@onready var size_label: Label = $PanelContainer/MarginContainer/VBoxContainer/GridLabel
@onready var difficulty_label: Label = $PanelContainer/MarginContainer/VBoxContainer/WallDensityLabel
@onready var moves_label: Label = $PanelContainer/MarginContainer/VBoxContainer/TurnsLabel
@onready var solution_label: Label = $PanelContainer/MarginContainer/VBoxContainer/KeyLabel
@onready var seed_label: Label = $PanelContainer/MarginContainer/VBoxContainer/InventoryLabel
@onready var status_label: Label = $PanelContainer/MarginContainer/VBoxContainer/StatusLabel
@onready var message_label: Label = $PanelContainer/MarginContainer/VBoxContainer/MessageLabel
@onready var transition_overlay: Control = $TransitionOverlay


func _ready() -> void:
	hide_loading_screen()


func update_state(state: Dictionary) -> void:
	board_label.text = "Board: %dx%d" % [state.get("grid_width", 0), state.get("grid_height", 0)]
	size_label.text = "Size Bucket: %s" % String(state.get("size_category", "small")).capitalize()
	difficulty_label.text = "Difficulty: %s" % String(state.get("difficulty", "easy")).capitalize()
	moves_label.text = "Moves: %d" % int(state.get("moves_taken", 0))
	solution_label.text = "Shortest Solution: %d" % int(state.get("solution_total_steps", 0))
	seed_label.text = "Seed ID: %s" % String(state.get("seed_id", "N/A"))
	status_label.text = "Status: %s" % String(state.get("status", "In progress"))


func set_message(text: String) -> void:
	message_label.text = text


func show_loading_screen() -> void:
	transition_overlay.visible = true


func hide_loading_screen() -> void:
	transition_overlay.visible = false
