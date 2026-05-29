from __future__ import annotations

from dataclasses import dataclass

from .grid import MazeLayout
from .models import Coord, EnemyRuntimeState, EnemySpec, GameState
from .rules import GreedyChaserRules


@dataclass(frozen=True, slots=True)
class SolverContext:
    rules: GreedyChaserRules
    layout: MazeLayout
    goal: Coord
    enemy_specs: tuple[EnemySpec, ...]
    trap_lookup: frozenset[Coord]
    initial_state: GameState


def build_solver_context(
    rules: GreedyChaserRules,
    layout: MazeLayout,
    player_start: Coord,
    enemy_starts: tuple[Coord, ...],
    goal: Coord,
    enemy_specs: tuple[EnemySpec, ...] | None = None,
    trap_cells: tuple[Coord, ...] = (),
) -> SolverContext:
    resolved_specs = normalize_enemy_specs(rules, enemy_starts, enemy_specs)
    return SolverContext(
        rules=rules,
        layout=layout,
        goal=goal,
        enemy_specs=resolved_specs,
        trap_lookup=frozenset(trap_cells),
        initial_state=GameState(
            player_position=player_start,
            enemy_positions=enemy_starts,
            enemy_states=initial_enemy_states(resolved_specs),
        ),
    )


def normalize_enemy_specs(
    rules: GreedyChaserRules,
    enemy_starts: tuple[Coord, ...],
    enemy_specs: tuple[EnemySpec, ...] | None,
) -> tuple[EnemySpec, ...]:
    if enemy_specs is not None:
        return enemy_specs
    return tuple(
        EnemySpec(move_priority=rules.move_priority, step_count=rules.minotaur_steps)
        for _ in enemy_starts
    )


def initial_enemy_states(enemy_specs: tuple[EnemySpec, ...]) -> tuple[EnemyRuntimeState, ...]:
    return tuple(EnemyRuntimeState(facing_index=spec.facing_index) for spec in enemy_specs)
