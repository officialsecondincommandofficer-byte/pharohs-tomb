from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from .grid import MazeLayout
from .models import Coord, EnemyRuntimeState, EnemySpec

if TYPE_CHECKING:
    from .enemy_turn_rules import EnemyTurnRules


@dataclass(frozen=True, slots=True)
class EnemyStepResult:
    caught_player: bool
    next_state: EnemyRuntimeState


class EnemyBehavior(Protocol):
    def initial_behavior_state(self, spec: EnemySpec): ...

    def choose_spawn_cell(
        self,
        spec: EnemySpec,
        player_location: Coord,
        occupied_cells: set[Coord],
    ) -> Coord | None: ...

    def step_enemy(
        self,
        engine: EnemyTurnRules,
        layout: MazeLayout,
        player_location: Coord,
        enemy_index: int,
        enemy_positions: list[Coord | None],
        enemy_states: list[EnemyRuntimeState],
        enemy_specs: tuple[EnemySpec, ...],
        spec: EnemySpec,
    ) -> EnemyStepResult: ...
