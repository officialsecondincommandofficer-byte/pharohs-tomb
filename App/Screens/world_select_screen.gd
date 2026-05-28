extends Control

signal world_confirmed(world_definition)
signal back_requested

@onready var title_label: Label = $MarginContainer/VBoxContainer/HeaderLabel
@onready var item_list: ItemList = $MarginContainer/VBoxContainer/ContentContainer/WorldList
@onready var detail_label: RichTextLabel = $MarginContainer/VBoxContainer/ContentContainer/DetailPanel/MarginContainer/DetailLabel
@onready var open_button: Button = $MarginContainer/VBoxContainer/FooterContainer/OpenButton
@onready var back_button: Button = $MarginContainer/VBoxContainer/FooterContainer/BackButton

var _worlds: Array = []


func _ready() -> void:
	item_list.item_selected.connect(_on_item_selected)
	item_list.item_activated.connect(_on_item_activated)
	open_button.pressed.connect(_on_open_pressed)
	back_button.pressed.connect(_on_back_pressed)
	_refresh()


func configure_worlds(worlds: Array) -> void:
	_worlds = worlds
	if is_node_ready():
		_refresh()


func _refresh() -> void:
	if not is_node_ready():
		return

	item_list.clear()
	for world_definition in _worlds:
		item_list.add_item("%s (%d levels)" % [world_definition.display_name, world_definition.level_count()])

	title_label.text = "World Select"
	open_button.disabled = _worlds.is_empty()

	if _worlds.is_empty():
		detail_label.text = "[b]No worlds found.[/b]\n\nAdd a manifest-driven world under [code]Resources/Worlds[/code]."
		return

	item_list.select(0)
	_update_detail(0)


func _update_detail(index: int) -> void:
	if index < 0 or index >= _worlds.size():
		detail_label.text = ""
		return

	var world_definition = _worlds[index]
	var description = world_definition.description
	if description.is_empty():
		description = "No description provided."

	detail_label.text = (
		"[b]%s[/b]\n%d levels\nSource: %s\n\n%s" % [
			world_definition.display_name,
			world_definition.level_count(),
			world_definition.source_type,
			description,
		]
	)


func _selected_index() -> int:
	var selected := item_list.get_selected_items()
	if selected.is_empty():
		return -1
	return int(selected[0])


func _on_item_selected(index: int) -> void:
	_update_detail(index)


func _on_item_activated(index: int) -> void:
	if index < 0 or index >= _worlds.size():
		return
	world_confirmed.emit(_worlds[index])


func _on_open_pressed() -> void:
	var index := _selected_index()
	if index < 0:
		return
	world_confirmed.emit(_worlds[index])


func _on_back_pressed() -> void:
	back_requested.emit()
