extends RefCounted
class_name SamuraiBehaviorState

var facing_index: int = 2
var attack_phase: int = -1
var turns_until_dash: int = 0


func to_dictionary() -> Dictionary:
	return {
		"facing_index": facing_index,
		"attack_phase": attack_phase,
		"turns_until_dash": turns_until_dash,
	}


func from_dictionary(state: Dictionary) -> void:
	facing_index = int(state.get("facing_index", facing_index))
	attack_phase = int(state.get("attack_phase", attack_phase))
	turns_until_dash = int(state.get("turns_until_dash", turns_until_dash))
