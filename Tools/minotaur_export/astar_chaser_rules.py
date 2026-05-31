from __future__ import annotations

from heapq import heappop, heappush

from .enemy_behavior import EnemyBehavior, EnemyStepResult
from .grid import MazeLayout
from .models import AStarBehaviorState, Coord, EnemyRuntimeState, EnemySpec
from .movement import apply_enemy_action, available_enemy_actions


def choose_astar_step(
    layout: MazeLayout,
    player_location: Coord,
    enemy_location: Coord,
    blocked_cells: set[Coord],
) -> Coord:
    if enemy_location == player_location:
        return enemy_location

    frontier: list[tuple[int, int, Coord]] = []
    heappush(frontier, (_manhattan_distance(enemy_location, player_location), 0, enemy_location))
    came_from: dict[Coord, Coord | None] = {enemy_location: None}
    g_score: dict[Coord, int] = {enemy_location: 0}

    while frontier:
        _, _, current = heappop(frontier)
        if current == player_location:
            break

        for action in available_enemy_actions(layout, current, include_skip=False):
            neighbor = apply_enemy_action(layout, current, action)
            if neighbor == current or (neighbor in blocked_cells and neighbor != player_location):
                continue
            tentative_cost = g_score[current] + 1
            if tentative_cost >= g_score.get(neighbor, 1_000_000):
                continue
            came_from[neighbor] = current
            g_score[neighbor] = tentative_cost
            heappush(frontier, (tentative_cost + _manhattan_distance(neighbor, player_location), tentative_cost, neighbor))

    if player_location not in came_from:
        return enemy_location

    cursor = player_location
    while came_from[cursor] is not None and came_from[cursor] != enemy_location:
        cursor = came_from[cursor]
    return cursor


def choose_spawn_cell(
    candidate_cells: tuple[Coord, ...],
    player_location: Coord,
    occupied_cells: set[Coord],
) -> Coord | None:
    available = [cell for cell in candidate_cells if cell not in occupied_cells]
    if not available:
        return None
    ranked = sorted(available, key=lambda cell: (-_manhattan_distance(cell, player_location), cell[1], cell[0]))
    return ranked[0]


def _manhattan_distance(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class AStarChaserBehavior(EnemyBehavior):
    def initial_behavior_state(self, spec: EnemySpec) -> AStarBehaviorState:
        del spec
        return AStarBehaviorState()

    def choose_spawn_cell(
        self,
        spec: EnemySpec,
        player_location: Coord,
        occupied_cells: set[Coord],
    ) -> Coord | None:
        if spec.spawn_cell is None:
            return None
        return choose_spawn_cell((spec.spawn_cell,), player_location, occupied_cells)

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
            choose_next_cell=lambda current_location, blocked_cells: choose_astar_step(
                layout=layout,
                player_location=player_location,
                enemy_location=current_location,
                blocked_cells=blocked_cells,
            ),
        )
        return EnemyStepResult(caught_player=caught_player, next_state=enemy_states[enemy_index])
