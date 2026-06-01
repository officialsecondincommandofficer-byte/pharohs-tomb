extends RefCounted
class_name EnemyLifecycleSystem


static func resolve_activation(activated: bool, wake_goal_distance: int, player_cell: Vector2i, board_state) -> bool:
	if activated:
		return true
	if wake_goal_distance < 0:
		return true
	var distance_to_exit: int = int(board_state.goal_distance_from_player_cell(player_cell))
	return distance_to_exit >= 0 and distance_to_exit <= wake_goal_distance


static func advance_lifetime(activated: bool, lifetime_turns: int, turns_remaining: int, is_dead: bool) -> Dictionary:
	if not activated or lifetime_turns < 0 or is_dead:
		return {
			"turns_remaining": turns_remaining,
			"expired": false,
		}
	var next_turns_remaining := turns_remaining - 1
	return {
		"turns_remaining": next_turns_remaining,
		"expired": next_turns_remaining <= 0,
	}
