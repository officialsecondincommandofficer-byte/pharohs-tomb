extends CanvasLayer

@onready var floor_label: Label = $PanelContainer/MarginContainer/VBoxContainer/FloorLabel
@onready var grid_label: Label = $PanelContainer/MarginContainer/VBoxContainer/GridLabel
@onready var wall_density_label: Label = $PanelContainer/MarginContainer/VBoxContainer/WallDensityLabel
@onready var turns_label: Label = $PanelContainer/MarginContainer/VBoxContainer/TurnsLabel
@onready var key_label: Label = $PanelContainer/MarginContainer/VBoxContainer/KeyLabel
@onready var inventory_label: Label = $PanelContainer/MarginContainer/VBoxContainer/InventoryLabel
@onready var message_label: Label = $PanelContainer/MarginContainer/VBoxContainer/MessageLabel


func update_state(state: Dictionary) -> void:
	floor_label.text = "Floor: %d / %d" % [state.get("floor", 1), state.get("total_floors", 1)]
	grid_label.text = "Grid: %dx%d" % [state.get("grid_width", 0), state.get("grid_height", 0)]
	wall_density_label.text = "Walls: %d%%" % int(round(float(state.get("wall_density", 0.0)) * 100.0))
	turns_label.text = "Turns Remaining: %d" % state.get("turns_remaining", 0)
	key_label.text = "Key: %s" % ("Collected" if state.get("has_key", false) else "Missing")

	var inventory: Array = state.get("inventory", [])
	var inventory_text := "Inventory: Empty"
	if not inventory.is_empty():
		inventory_text = "Inventory: %s" % ", ".join(inventory)
	inventory_label.text = inventory_text


func set_message(text: String) -> void:
	message_label.text = text
