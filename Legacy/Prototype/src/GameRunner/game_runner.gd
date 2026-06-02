extends Node

@export var stages: Array[PackedScene]
var current_stage_index := 0

@export var player_scene: PackedScene

@export var enemies: Array[PackedScene]
var current_enemy_index := 0

var current_stage: Node = null

func _ready() -> void:
	_start_new_game()


func _start_new_game():
	# 1. Load the stage
	current_stage = stages[0].instantiate()
	add_child(current_stage)
	current_stage.scale = Vector2(3, 3)

	# 2. Get spawn markers from the stage
	var player_spawn = current_stage.get_node("PlayerSpawn")
	var enemy_spawn = current_stage.get_node("EnemySpawn")

	# 3. Spawn the player
	var player = player_scene.instantiate()
	player.position = player_spawn.position
	current_stage.add_child(player)

	# 4. Spawn the enemy
	var enemy = enemies[0].instantiate()
	enemy.position = enemy_spawn.position
	current_stage.add_child(enemy)
