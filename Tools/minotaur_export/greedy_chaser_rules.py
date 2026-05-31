from __future__ import annotations

from .enemy_behavior import EnemyBehavior, EnemyStepResult
from .grid import MazeLayout
from .models import Coord, EnemyRuntimeState, EnemySpec
from .movement import apply_enemy_action, available_enemy_actions


def choose_greedy_step(
    layout: MazeLayout,
    player_location: Coord,
    enemy_location: Coord,
    move_priority: str,
    blocked_cells: set[Coord],
) -> Coord:
    options = set(available_enemy_actions(layout, enemy_location, include_skip=False))
    options = {option for option in options if apply_enemy_action(layout, enemy_location, option) not in blocked_cells}

    for axis in preferred_axes(move_priority):
        next_cell = greedy_axis_step(enemy_location, player_location, axis, options)
        if next_cell != enemy_location:
            return next_cell

    return enemy_location


def preferred_axes(move_priority: str) -> tuple[str, str]:
    if move_priority == "vertical":
        return ("vertical", "horizontal")
    if move_priority == "horizontal":
        return ("horizontal", "vertical")
    raise ValueError(f"Unsupported move priority: {move_priority}")


def greedy_axis_step(enemy: Coord, player_location: Coord, axis: str, options: set[str]) -> Coord:
    if axis == "horizontal":
        if "right" in options and player_location[0] > enemy[0]:
            return (enemy[0] + 1, enemy[1])
        if "left" in options and player_location[0] < enemy[0]:
            return (enemy[0] - 1, enemy[1])

    if axis == "vertical":
        if "up" in options and player_location[1] < enemy[1]:
            return (enemy[0], enemy[1] - 1)
        if "down" in options and player_location[1] > enemy[1]:
            return (enemy[0], enemy[1] + 1)

    return enemy


class GreedyChaserBehavior(EnemyBehavior):
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
        layout: MazeLayout,
        player_location: Coord,
        enemy_index: int,
        enemy_positions: list[Coord | None],
        enemy_states: list[EnemyRuntimeState],
        enemy_specs: tuple[EnemySpec, ...],
        spec: EnemySpec,
    ) -> EnemyStepResult:
        caught_player = engine.step_pathing_enemy(
            layout=layout,
            player_location=player_location,
            enemy_index=enemy_index,
            enemy_positions=enemy_positions,
            enemy_states=enemy_states,
            enemy_specs=enemy_specs,
            choose_next_cell=lambda current_location, blocked_cells: choose_greedy_step(
                layout=layout,
                player_location=player_location,
                enemy_location=current_location,
                move_priority=spec.move_priority,
                blocked_cells=blocked_cells,
            ),
        )
        return EnemyStepResult(caught_player=caught_player, next_state=enemy_states[enemy_index])
