extends RefCounted
class_name WorldTurnSystem


static func resolve_player_action(board_state, runtime_registry, action_name: String, player, enemy_manager) -> Dictionary:
	var next_state = runtime_registry.duplicate_runtime_state()
	var current_player: Vector2i = next_state.player_state.current_cell
	var transition: Dictionary = board_state.resolve_player_transition(current_player, action_name)
	var stepped_player: Vector2i = transition.get("stepped_cell", current_player)
	var next_player: Vector2i = transition.get("resolved_cell", current_player)
	if stepped_player == current_player and action_name != "skip":
		return {
			"consumed": false,
			"message": "That move is blocked.",
		}

	next_state.player_state.restore_to_cell(stepped_player, true)
	if stepped_player != current_player:
		await player.present_move_to_cell(stepped_player)
	else:
		next_state.player_state.apply_to_player(player)

	next_state.move_count += 1
	if board_state.is_trap_cell(stepped_player):
		next_state.player_state.mark_dead()
		next_state.game_over = true
		runtime_registry.commit_runtime_state(next_state, action_name)
		runtime_registry.apply_to_runtime(player, enemy_manager)
		return {
			"consumed": true,
			"status_text": "You lose",
			"message": "YOU LOSE!",
			"player_cell": stepped_player,
			"enemy_results": [],
			"game_over": true,
		}

	enemy_manager.restore_runtime_payload(next_state.enemy_phase_runtime_payload)
	var enemy_results: Array = await enemy_manager.begin_enemy_phase(stepped_player)
	next_state.enemy_phase_runtime_payload = enemy_manager.export_runtime_payload()

	var enemy_contacted_player := false
	for enemy_result in enemy_results:
		if bool(enemy_result.get("contact_player", false)):
			enemy_contacted_player = true
			break

	if enemy_contacted_player or enemy_manager.any_enemy_at_cell(stepped_player):
		next_state.player_state.mark_dead()
		next_state.game_over = true
		runtime_registry.commit_runtime_state(next_state, action_name)
		runtime_registry.apply_to_runtime(player, enemy_manager)
		return {
			"consumed": true,
			"status_text": "You lose",
			"message": "YOU LOSE!",
			"player_cell": stepped_player,
			"enemy_results": enemy_results,
			"game_over": true,
		}

	var turn_end_transition: Dictionary = board_state.resolve_player_turn_end_transition(next_player)
	next_player = turn_end_transition.get("resolved_cell", next_player)
	next_state.player_state.restore_to_cell(next_player, true)

	var status_text := "In progress"
	var message := ""
	if board_state.is_trap_cell(next_player):
		next_state.player_state.mark_dead()
		next_state.game_over = true
		status_text = "You lose"
		message = "YOU LOSE!"
	elif board_state.is_exit_cell(next_player):
		next_state.game_over = true
		status_text = "You win"
		message = "YOU WIN!"
	else:
		next_state.game_over = false

	runtime_registry.commit_runtime_state(next_state, action_name)
	runtime_registry.apply_to_runtime(player, enemy_manager)

	return {
		"consumed": true,
		"status_text": status_text,
		"message": message,
		"player_cell": next_player,
		"enemy_results": enemy_results,
		"game_over": next_state.game_over,
	}
