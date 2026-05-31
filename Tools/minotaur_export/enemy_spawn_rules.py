from __future__ import annotations

from dataclasses import replace

from .enemy_behavior import EnemyBehavior
from .models import Coord, EnemyRuntimeState, EnemySpec


def advance_spawn_state(
    behavior: EnemyBehavior,
    spec: EnemySpec,
    state: EnemyRuntimeState,
    player_location: Coord,
    enemy_positions: list[Coord | None],
) -> tuple[Coord | None, EnemyRuntimeState]:
    if state.turns_until_spawn <= 0 or spec.spawn_cell is None:
        return None, state

    next_turns_until_spawn = state.turns_until_spawn - 1
    if next_turns_until_spawn > 0:
        return None, replace(state, turns_until_spawn=next_turns_until_spawn)

    occupied_cells = {position for position in enemy_positions if position is not None}
    spawn_cell = behavior.choose_spawn_cell(spec, player_location, occupied_cells)
    if spawn_cell is None:
        return None, replace(state, turns_until_spawn=1)

    return spawn_cell, replace(
        state,
        activated=spec.wake_goal_distance < 0,
        turns_until_spawn=0,
    )
