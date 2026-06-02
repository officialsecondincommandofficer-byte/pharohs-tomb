extends RefCounted
class_name WorldBoardEffectRuntimePayload

var mutable_effects: Array[Dictionary] = []


func configure(next_mutable_effects: Array[Dictionary]) -> WorldBoardEffectRuntimePayload:
	mutable_effects = _duplicate_dictionary_array(next_mutable_effects)
	return self


func from_dictionary(payload: Dictionary) -> WorldBoardEffectRuntimePayload:
	return configure(_duplicate_dictionary_array(payload.get("mutable_effects", [])))


func to_dictionary() -> Dictionary:
	return {
		"mutable_effects": _duplicate_dictionary_array(mutable_effects),
	}


func duplicate_payload() -> WorldBoardEffectRuntimePayload:
	return get_script().new().configure(mutable_effects)


static func _duplicate_dictionary_array(entries) -> Array[Dictionary]:
	var duplicated: Array[Dictionary] = []
	for entry in entries:
		if entry is Dictionary:
			duplicated.append(entry.duplicate(true))
	return duplicated
