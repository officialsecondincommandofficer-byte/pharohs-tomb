from __future__ import annotations

from dataclasses import replace

from .enemy_behavior import EnemyBehavior
from .models import EnemyRuntimeState, EnemySpec, SpawnedEnemyState, ZoneSpawnerSpec, ZoneSpawnerState


def advance_zone_spawner(
    spawner: ZoneSpawnerSpec,
    state: ZoneSpawnerState,
    behavior: EnemyBehavior,
    player_location,
    occupied_cells: set[tuple[int, int]],
) -> tuple[ZoneSpawnerState, SpawnedEnemyState | None]:
    next_turns_until_spawn = state.turns_until_spawn - 1
    if next_turns_until_spawn > 0:
        return replace(state, turns_until_spawn=next_turns_until_spawn), None

    spawn_spec = replace(
        spawner.enemy_spec,
        spawn_cell=None,
    )
    spawn_cell = behavior.choose_spawn_cell(
        replace(spawn_spec, spawn_cell=spawner.spawn_candidates[0] if len(spawner.spawn_candidates) == 1 else None),
        player_location,
        occupied_cells,
    )
    if spawn_cell is None:
        spawn_cell = _choose_spawn_cell(spawner.spawn_candidates, player_location, occupied_cells, behavior, spawner.enemy_spec)
    if spawn_cell is None:
        return ZoneSpawnerState(turns_until_spawn=1), None

    runtime_state = EnemyRuntimeState(
        activated=spawner.enemy_spec.wake_goal_distance < 0,
        turns_remaining=spawner.enemy_spec.lifetime_turns,
        behavior_state=behavior.initial_behavior_state(spawner.enemy_spec),
    )
    return (
        ZoneSpawnerState(turns_until_spawn=spawner.spawn_interval_turns),
        SpawnedEnemyState(
            spec=replace(spawner.enemy_spec, spawn_cell=spawn_cell, spawn_delay_turns=0, respawn_delay_turns=0),
            position=spawn_cell,
            runtime_state=runtime_state,
            source_spawner_id=spawner.spawner_id,
        ),
    )


def _choose_spawn_cell(
    candidates,
    player_location,
    occupied_cells,
    behavior: EnemyBehavior,
    spec: EnemySpec,
):
    chosen = None
    for candidate in candidates:
        attempt = behavior.choose_spawn_cell(replace(spec, spawn_cell=candidate), player_location, occupied_cells)
        if attempt is None:
            continue
        chosen = attempt
        break
    return chosen
