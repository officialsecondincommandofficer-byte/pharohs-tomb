from __future__ import annotations

from .enemy_behavior import EnemyBehavior, EnemyStepResult
from .models import Coord, EnemyRuntimeState, EnemySpec


class StationaryBehavior(EnemyBehavior):
    def initial_behavior_state(self, spec: EnemySpec):
        del spec
        return None

    def choose_spawn_cell(
        self,
        spec: EnemySpec,
        player_location: Coord,
        occupied_cells: set[Coord],
    ) -> Coord | None:
        del player_location
        if spec.spawn_cell is None or spec.spawn_cell in occupied_cells:
            return None
        return spec.spawn_cell

    def step_enemy(
        self,
        engine,
        layout,
        player_location: Coord,
        enemy_index: int,
        enemy_positions: list[Coord | None],
        enemy_states: list[EnemyRuntimeState],
        enemy_specs: tuple[EnemySpec, ...],
        spec: EnemySpec,
    ) -> EnemyStepResult:
        del engine, layout, player_location, enemy_positions, enemy_specs, spec
        return EnemyStepResult(caught_player=False, next_state=enemy_states[enemy_index])
