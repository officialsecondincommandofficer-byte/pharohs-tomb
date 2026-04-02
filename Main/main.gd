extends Node2D

@onready var game_manager: Node = $GameManager


func _ready() -> void:
	game_manager.bootstrap({
		"camera": $GameCamera,
		"maze_generator": $MazeGenerator,
		"tile_map": $TileMap,
		"fog_of_war": $FogOfWar,
		"player": $Player,
		"enemy_manager": $EnemyManager,
		"item_layer": $ItemLayer,
		"hud": $HUD,
	})


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_R:
		game_manager.restart_run()
