extends Node2D
@export var player_scene: PackedScene
@export var enemy_scene: PackedScene

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	spawn_player()
	spawn_enemy

func spawn_player():
	var player = player_scene.instantiate()
	player.position = $PlayerSpawn.position
	add_child(player)
	
func spawn_enemy():
	var enemy = enemy_scene.instantiate()
	enemy.position = $EnemySpawn.position
	add_child(enemy)
	
# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	pass
