extends CharacterBody2D

@export var move_speed := 100
@onready var anim := $AnimatedSprite2D

func _physics_process(delta):
	var input_vector = Vector2.ZERO

	input_vector.x = Input.get_action_strength("ui_right") - Input.get_action_strength("ui_left")
	input_vector.y = Input.get_action_strength("ui_down") - Input.get_action_strength("ui_up")

	if input_vector != Vector2.ZERO:
		input_vector = input_vector.normalized()
		velocity = input_vector * move_speed
		play_walk_animation(input_vector)
	else:
		velocity = Vector2.ZERO
		anim.stop()
		anim.frame = 1 

	move_and_slide()


func play_walk_animation(dir: Vector2):
	if abs(dir.x) > abs(dir.y):
		if dir.x > 0:
			anim.play("walk_right")
		else:
			anim.play("walk_left")
	else:
		if dir.y > 0:
			anim.play("walk_downward")
		else:
			anim.play("walk_upward")
