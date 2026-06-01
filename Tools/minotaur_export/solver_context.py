from __future__ import annotations

from dataclasses import dataclass

from .grid import MazeLayout
from .models import Coord, EnemyRuntimeState, EnemySpec, GameState, ZoneSpawnerSpec, ZoneSpawnerState
from .rules import GreedyChaserRules


@dataclass(frozen=True, slots=True)
class SolverContext:
    rules: GreedyChaserRules
    layout: MazeLayout
    goal: Coord
    goal_cells: tuple[Coord, ...]
    enemy_specs: tuple[EnemySpec, ...]
    zone_spawners: tuple[ZoneSpawnerSpec, ...]
    trap_lookup: frozenset[Coord]
    initial_state: GameState


def build_solver_context(
    rules: GreedyChaserRules,
    layout: MazeLayout,
    player_start: Coord,
    enemy_starts: tuple[Coord | None, ...],
    goal: Coord,
    goal_cells: tuple[Coord, ...] = (),
    enemy_specs: tuple[EnemySpec, ...] | None = None,
    zone_spawners: tuple[ZoneSpawnerSpec, ...] = (),
    trap_cells: tuple[Coord, ...] = (),
) -> SolverContext:
    resolved_specs = normalize_enemy_specs(rules, enemy_starts, enemy_specs)
    resolved_goal_cells = goal_cells or (goal,)
    return SolverContext(
        rules=rules,
        layout=layout,
        goal=goal,
        goal_cells=resolved_goal_cells,
        enemy_specs=resolved_specs,
        zone_spawners=zone_spawners,
        trap_lookup=frozenset(trap_cells),
        initial_state=GameState(
            player_position=player_start,
            enemy_positions=enemy_starts,
            enemy_states=initial_enemy_states(resolved_specs),
            spawner_states=tuple(initial_spawner_states(zone_spawners)),
        ),
    )


def normalize_enemy_specs(
    rules: GreedyChaserRules,
    enemy_starts: tuple[Coord | None, ...],
    enemy_specs: tuple[EnemySpec, ...] | None,
) -> tuple[EnemySpec, ...]:
    if enemy_specs is not None:
        return enemy_specs
    return tuple(
        EnemySpec(move_priority=rules.move_priority, step_count=rules.minotaur_steps)
        for _ in enemy_starts
    )


def initial_enemy_states(enemy_specs: tuple[EnemySpec, ...]) -> tuple[EnemyRuntimeState, ...]:
    return tuple(rules_initial_enemy_state(spec) for spec in enemy_specs)


def initial_spawner_states(zone_spawners: tuple[ZoneSpawnerSpec, ...]) -> tuple[ZoneSpawnerState, ...]:
    return tuple(
        ZoneSpawnerState(
            turns_until_spawn=spawner.initial_delay_turns
            if spawner.initial_delay_turns >= 0
            else spawner.spawn_interval_turns
        )
        for spawner in zone_spawners
    )


def rules_initial_enemy_state(spec: EnemySpec) -> EnemyRuntimeState:
    return EnemyRuntimeState(
        activated=spec.component_int("activation", "wake_goal_distance", spec.wake_goal_distance) < 0
        and spec.component_int("activation", "spawn_delay_turns", spec.spawn_delay_turns) <= 0,
        turns_remaining=spec.component_int("lifecycle", "lifetime_turns", spec.lifetime_turns),
        turns_until_spawn=spec.component_int("activation", "spawn_delay_turns", spec.spawn_delay_turns),
    )
