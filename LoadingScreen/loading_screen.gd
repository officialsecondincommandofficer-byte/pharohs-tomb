extends CanvasLayer

const LOADING_SPLASH_PHRASES := [
	"Brushing sand off the save files...",
	"Convincing the mummy to stay in his lane.",
	"Polishing the golden sarcophagus.",
	"Teaching the scarabs to behave.",
	"Loading... please don't trigger any curses.",
	"Rebinding ancient glyphs to WASD.",
	"Negotiating with the undead union.",
	"Dusting off 3,000 years of bugs.",
	"Sacrificing frame rate to the sun god.",
	"Ensuring the traps meet modern safety standards.",
	"This tomb was definitely not built to code.",
	"If you hear footsteps behind you... run.",
	"Loading... because teleportation magic is unreliable.",
	"Fun fact: mummies do not appreciate speedrunners.",
	"The Pharaoh insists this is all historically accurate.",
	"Please remain calm. The curses rarely activate.",
]

@export var minimum_display_time: float = 2.0

@onready var title_label: Label = $Overlay/CenterContainer/PanelContainer/MarginContainer/VBoxContainer/LoadingTitleLabel
@onready var detail_label: RichTextLabel = $Overlay/CenterContainer/PanelContainer/MarginContainer/VBoxContainer/LoadingDetailLabel

var _shown_at_msec: int = 0


func _ready() -> void:
	hide_immediately()


func show_loading_screen(title: String = "Descending...", detail: String = "") -> void:
	title_label.text = title
	var splash_text := detail
	if splash_text.is_empty():
		splash_text = LOADING_SPLASH_PHRASES[randi() % LOADING_SPLASH_PHRASES.size()]
	detail_label.text = "[i]%s[/i]" % splash_text
	visible = true
	_shown_at_msec = Time.get_ticks_msec()


func hide_loading_screen() -> void:
	var elapsed_seconds: float = float(Time.get_ticks_msec() - _shown_at_msec) / 1000.0
	var remaining_seconds: float = max(0.0, minimum_display_time - elapsed_seconds)
	if remaining_seconds > 0.0:
		await get_tree().create_timer(remaining_seconds).timeout
	visible = false


func hide_immediately() -> void:
	visible = false
	_shown_at_msec = 0
