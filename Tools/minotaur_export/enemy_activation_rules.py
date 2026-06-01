from __future__ import annotations

from dataclasses import replace

from .models import Coord, EnemyRuntimeState, EnemySpec


def update_activation_state(
    spec: EnemySpec,
    state: EnemyRuntimeState,
    player_location: Coord,
    goal_cells: tuple[Coord, ...],
) -> EnemyRuntimeState:
    wake_goal_distance = spec.component_int("activation", "wake_goal_distance", spec.wake_goal_distance)
    if state.activated:
        return state
    if wake_goal_distance >= 0 and goal_cells:
        if min(manhattan_distance(player_location, goal) for goal in goal_cells) > wake_goal_distance:
            return state
    return replace(state, activated=True)


def advance_lifetime(
    spec: EnemySpec,
    state: EnemyRuntimeState,
    enemy_positions: list[Coord | None],
    enemy_index: int,
) -> EnemyRuntimeState:
    lifetime_turns = spec.component_int("lifecycle", "lifetime_turns", spec.lifetime_turns)
    respawn_delay_turns = spec.component_int("activation", "respawn_delay_turns", spec.respawn_delay_turns)
    if not state.activated or lifetime_turns < 0 or enemy_positions[enemy_index] is None:
        return state
    next_turns_remaining = state.turns_remaining - 1
    if next_turns_remaining <= 0:
        enemy_positions[enemy_index] = None
        if respawn_delay_turns > 0:
            return EnemyRuntimeState(
                activated=False,
                turns_remaining=lifetime_turns,
                turns_until_spawn=respawn_delay_turns,
                behavior_state=state.behavior_state,
            )
        return EnemyRuntimeState()
    return replace(state, turns_remaining=next_turns_remaining)


def manhattan_distance(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
