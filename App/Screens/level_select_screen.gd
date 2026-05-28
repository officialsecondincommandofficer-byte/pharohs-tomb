extends Control

signal level_confirmed(level_definition)
signal back_requested

@onready var title_label: Label = $MarginContainer/VBoxContainer/HeaderLabel
@onready var item_list: ItemList = $MarginContainer/VBoxContainer/ContentContainer/LevelList
@onready var detail_label: RichTextLabel = $MarginContainer/VBoxContainer/ContentContainer/DetailPanel/MarginContainer/DetailLabel
@onready var start_button: Button = $MarginContainer/VBoxContainer/FooterContainer/StartButton
@onready var back_button: Button = $MarginContainer/VBoxContainer/FooterContainer/BackButton

var _world_definition = null


func _ready() -> void:
	item_list.item_selected.connect(_on_item_selected)
	item_list.item_activated.connect(_on_item_activated)
	start_button.pressed.connect(_on_start_pressed)
	back_button.pressed.connect(_on_back_pressed)
	_refresh()


func configure_world(world_definition) -> void:
	_world_definition = world_definition
	if is_node_ready():
		_refresh()


func _refresh() -> void:
	if not is_node_ready():
		return

	item_list.clear()
	if _world_definition == null:
		title_label.text = "Level Select"
		start_button.disabled = true
		detail_label.text = ""
		return

	title_label.text = "Level Select: %s" % _world_definition.display_name
	for level_definition in _world_definition.levels:
		item_list.add_item(level_definition.list_label())

	start_button.disabled = _world_definition.levels.is_empty()
	if _world_definition.levels.is_empty():
		detail_label.text = "[b]No levels found for this world.[/b]"
		return

	item_list.select(0)
	_update_detail(0)


func _update_detail(index: int) -> void:
	if _world_definition == null:
		detail_label.text = ""
		return
	if index < 0 or index >= _world_definition.levels.size():
		detail_label.text = ""
		return

	var level_definition = _world_definition.levels[index]
	detail_label.text = (
		"[b]%s[/b]\nDifficulty: %s\nBoard: %dx%d\nShortest path: %d\n\n%s" % [
			level_definition.display_name,
			level_definition.difficulty.capitalize(),
			level_definition.width,
			level_definition.height,
			level_definition.solution_total_steps,
			level_definition.resource_path,
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
	if _world_definition == null:
		return
	if index < 0 or index >= _world_definition.levels.size():
		return
	level_confirmed.emit(_world_definition.levels[index])


func _on_start_pressed() -> void:
	if _world_definition == null:
		return
	var index := _selected_index()
	if index < 0:
		return
	level_confirmed.emit(_world_definition.levels[index])


func _on_back_pressed() -> void:
	back_requested.emit()
