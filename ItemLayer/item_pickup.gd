extends Node2D

@export var item_id: String = "item"
@export var glyph: String = "?"
@export var tint: Color = Color.WHITE

@onready var label: Label = $Label

var grid_cell: Vector2i = Vector2i.ZERO


func configure(cell: Vector2i, board_state) -> void:
	grid_cell = cell
	position = board_state.to_world(cell) + Vector2(-6, -10)
	label.text = glyph
	label.modulate = tint
