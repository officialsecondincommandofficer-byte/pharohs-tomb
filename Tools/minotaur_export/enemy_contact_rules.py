from __future__ import annotations

from .models import Coord, EnemySpec

KILLER_TRAIT = "killer"
CONTACT_BLOCKED = "blocked"
CONTACT_TARGET_DIES = "target_dies"
CONTACT_MOVER_DIES = "mover_dies"


def enemy_index_at_position(
    enemy_positions: list[Coord | None],
    target_position: Coord,
    excluded_index: int,
) -> int | None:
    for enemy_index, enemy_position in enumerate(enemy_positions):
        if enemy_index == excluded_index or enemy_position is None:
            continue
        if enemy_position == target_position:
            return enemy_index
    return None


def _is_killer(spec: EnemySpec) -> bool:
    contact_component = spec.component("contact")
    return contact_component.get("enemy_collision") == "kill_non_killers" or KILLER_TRAIT in spec.traits


def resolve_enemy_contact(
    mover_index: int,
    target_index: int,
    enemy_specs: tuple[EnemySpec, ...],
) -> str:
    mover_is_killer = _is_killer(enemy_specs[mover_index])
    target_is_killer = _is_killer(enemy_specs[target_index])

    if target_is_killer:
        if mover_is_killer and mover_index < target_index:
            return CONTACT_TARGET_DIES
        return CONTACT_MOVER_DIES

    if mover_is_killer:
        return CONTACT_TARGET_DIES

    return CONTACT_BLOCKED


def blocked_cells_for_mover(
    mover_index: int,
    enemy_positions: list[Coord | None],
    enemy_specs: tuple[EnemySpec, ...],
) -> set[Coord]:
    blocked_cells: set[Coord] = set()
    for target_index, target_position in enumerate(enemy_positions):
        if target_index == mover_index or target_position is None:
            continue
        if resolve_enemy_contact(mover_index, target_index, enemy_specs) == CONTACT_BLOCKED:
            blocked_cells.add(target_position)
    return blocked_cells
