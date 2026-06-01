extends RefCounted
class_name EnemyContactSystem

const TRAIT_KILLER := "killer"
const CONTACT_BLOCKED := "blocked"
const CONTACT_TARGET_DIES := "target_dies"
const CONTACT_MOVER_DIES := "mover_dies"


static func build_blocked_lookup(registry, mover_index: int) -> Dictionary:
	var blocked_lookup: Dictionary = {}
	for target_index in range(registry.size()):
		if target_index == mover_index:
			continue
		var target = registry.record_at(target_index)
		if not target.occupies_cell():
			continue
		if resolve_contact(registry.record_at(mover_index), target) == CONTACT_BLOCKED:
			blocked_lookup[target.current_cell] = true
	return blocked_lookup


static func active_enemy_index_at_cell(registry, cell: Vector2i, excluded_index: int) -> int:
	return registry.active_record_index_at_cell(cell, excluded_index)


static func resolve_contact(mover, target) -> String:
	var mover_is_killer: bool = mover.has_trait(TRAIT_KILLER)
	var target_is_killer: bool = target.has_trait(TRAIT_KILLER)

	if target_is_killer:
		if mover_is_killer and mover.spawn_order < target.spawn_order:
			return CONTACT_TARGET_DIES
		return CONTACT_MOVER_DIES

	if mover_is_killer:
		return CONTACT_TARGET_DIES

	return CONTACT_BLOCKED
