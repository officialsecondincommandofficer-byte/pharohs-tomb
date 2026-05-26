from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from functools import lru_cache

from .grid import MazeLayout
from .models import Coord, EnemyRuntimeState, EnemySpec, GameState, SolveResult
from .rules import GreedyChaserRules

ACTION_DELTAS: dict[Coord, str] = {
    (1, 0): "right",
    (-1, 0): "left",
    (0, -1): "up",
    (0, 1): "down",
}
OPTIMIZED_SOLVER_MIN_DIMENSION = 13


@lru_cache(maxsize=None)
def _goal_distances(layout: MazeLayout, goal: Coord) -> dict[Coord, int]:
    queue: deque[Coord] = deque([goal])
    distances = {goal: 0}

    while queue:
        cell = queue.popleft()
        next_distance = distances[cell] + 1
        for neighbor in layout.neighbors(cell):
            if layout.is_blocked(cell, neighbor) or neighbor in distances:
                continue
            distances[neighbor] = next_distance
            queue.append(neighbor)

    return distances


@lru_cache(maxsize=None)
def _shortest_layout_path(layout: MazeLayout, start: Coord, goal: Coord) -> tuple[str, ...] | None:
    if start == goal:
        return ()

    queue: deque[Coord] = deque([start])
    parents: dict[Coord, tuple[Coord | None, str | None]] = {start: (None, None)}

    while queue:
        cell = queue.popleft()
        for neighbor in layout.neighbors(cell):
            if layout.is_blocked(cell, neighbor) or neighbor in parents:
                continue

            delta = (neighbor[0] - cell[0], neighbor[1] - cell[1])
            parents[neighbor] = (cell, ACTION_DELTAS[delta])
            if neighbor == goal:
                return _reconstruct_cell_path(goal, parents)
            queue.append(neighbor)

    return None


def _reconstruct_cell_path(
    goal: Coord,
    parents: dict[Coord, tuple[Coord | None, str | None]],
) -> tuple[str, ...]:
    actions: list[str] = []
    cell: Coord | None = goal

    while cell is not None:
        previous, action = parents[cell]
        if action is not None:
            actions.append(action)
        cell = previous

    actions.reverse()
    return tuple(actions)


@dataclass(slots=True)
class BaseMazeSolver:
    rules: GreedyChaserRules = field(default_factory=GreedyChaserRules)

    def shortest_path_length_without_enemies(self, layout: MazeLayout, start: Coord, goal: Coord) -> int | None:
        return _goal_distances(layout, goal).get(start)

    def shortest_path_without_enemies(self, layout: MazeLayout, start: Coord, goal: Coord) -> tuple[str, ...] | None:
        return _shortest_layout_path(layout, start, goal)

    def sequence_is_safe(
        self,
        layout: MazeLayout,
        player_start: Coord,
        enemy_starts: tuple[Coord, ...],
        actions: tuple[str, ...],
        goal: Coord,
        enemy_specs: tuple[EnemySpec, ...],
        trap_cells: tuple[Coord, ...] = (),
    ) -> bool:
        trap_lookup = set(trap_cells)
        enemy_specs = self._normalize_enemy_specs(enemy_starts, enemy_specs)
        state = GameState(
            player_position=player_start,
            enemy_positions=enemy_starts,
            enemy_states=self._initial_enemy_states(enemy_specs),
        )

        for action in actions:
            state = self.rules.step_state(layout, state, action, enemy_specs)
            if state is None:
                return False
            if state.player_position in trap_lookup:
                return False

        return state.player_position == goal

    def _normalize_enemy_specs(
        self,
        enemy_starts: tuple[Coord, ...],
        enemy_specs: tuple[EnemySpec, ...] | None,
    ) -> tuple[EnemySpec, ...]:
        return enemy_specs or tuple(
            EnemySpec(move_priority=self.rules.move_priority, step_count=self.rules.minotaur_steps)
            for _ in enemy_starts
        )

    def _initial_enemy_states(self, enemy_specs: tuple[EnemySpec, ...]) -> tuple[EnemyRuntimeState, ...]:
        return tuple(EnemyRuntimeState(facing_index=spec.facing_index) for spec in enemy_specs)


@dataclass(slots=True)
class LegacyMazeSolver(BaseMazeSolver):
    def solve(
        self,
        layout: MazeLayout,
        player_start: Coord,
        enemy_starts: tuple[Coord, ...],
        goal: Coord,
        enemy_specs: tuple[EnemySpec, ...] | None = None,
        trap_cells: tuple[Coord, ...] = (),
    ) -> SolveResult:
        enemy_specs = self._normalize_enemy_specs(enemy_starts, enemy_specs)
        trap_lookup = set(trap_cells)
        initial_state = GameState(
            player_position=player_start,
            enemy_positions=enemy_starts,
            enemy_states=self._initial_enemy_states(enemy_specs),
        )
        if player_start == goal:
            return SolveResult(solvable=True, actions=())

        queue: deque[tuple[GameState, tuple[str, ...]]] = deque([(initial_state, ())])
        visited: set[GameState] = {initial_state}

        while queue:
            state, moves = queue.popleft()
            for action in self.rules.available_actions(layout, state.player_position, include_skip=True):
                next_state = self.rules.step_state(layout, state, action, enemy_specs)
                if next_state is None:
                    continue
                if next_state.player_position in trap_lookup:
                    continue

                next_moves = moves + (action,)
                if next_state.player_position == goal:
                    return SolveResult(solvable=True, actions=next_moves)
                if next_state in visited:
                    continue

                visited.add(next_state)
                queue.append((next_state, next_moves))

        return SolveResult(solvable=False, actions=())


@dataclass(slots=True)
class OptimizedMazeSolver(BaseMazeSolver):
    def solve(
        self,
        layout: MazeLayout,
        player_start: Coord,
        enemy_starts: tuple[Coord, ...],
        goal: Coord,
        enemy_specs: tuple[EnemySpec, ...] | None = None,
        trap_cells: tuple[Coord, ...] = (),
    ) -> SolveResult:
        enemy_specs = self._normalize_enemy_specs(enemy_starts, enemy_specs)
        trap_lookup = set(trap_cells)
        goal_distances = _goal_distances(layout, goal)
        initial_state = GameState(
            player_position=player_start,
            enemy_positions=enemy_starts,
            enemy_states=self._initial_enemy_states(enemy_specs),
        )
        if player_start == goal:
            return SolveResult(solvable=True, actions=())

        queue: deque[GameState] = deque([initial_state])
        parents: dict[GameState, tuple[GameState | None, str | None]] = {initial_state: (None, None)}

        while queue:
            state = queue.popleft()
            actions = self.rules.available_actions(layout, state.player_position, include_skip=True)
            ordered_actions = sorted(
                actions,
                key=lambda action: (
                    goal_distances.get(self.rules.apply_action(layout, state.player_position, action), float("inf")),
                    1 if action == "skip" else 0,
                ),
            )

            for action in ordered_actions:
                next_state = self.rules.step_state(layout, state, action, enemy_specs)
                if next_state is None:
                    continue
                if next_state.player_position in trap_lookup:
                    continue
                if next_state == state or next_state in parents:
                    continue

                parents[next_state] = (state, action)
                if next_state.player_position == goal:
                    return SolveResult(
                        solvable=True,
                        actions=self._reconstruct_actions(next_state, parents),
                    )
                queue.append(next_state)

        return SolveResult(solvable=False, actions=())

    def _reconstruct_actions(
        self,
        goal_state: GameState,
        parents: dict[GameState, tuple[GameState | None, str | None]],
    ) -> tuple[str, ...]:
        actions: list[str] = []
        state: GameState | None = goal_state

        while state is not None:
            previous, action = parents[state]
            if action is not None:
                actions.append(action)
            state = previous

        actions.reverse()
        return tuple(actions)


@dataclass(slots=True)
class MazeSolver(BaseMazeSolver):
    optimized_solver: OptimizedMazeSolver = field(default_factory=OptimizedMazeSolver)
    legacy_solver: LegacyMazeSolver = field(default_factory=LegacyMazeSolver)

    def __post_init__(self) -> None:
        self.optimized_solver.rules = self.rules
        self.legacy_solver.rules = self.rules

    def uses_optimized_search(self, layout: MazeLayout) -> bool:
        return max(layout.width, layout.height) >= OPTIMIZED_SOLVER_MIN_DIMENSION

    def solve(
        self,
        layout: MazeLayout,
        player_start: Coord,
        enemy_starts: tuple[Coord, ...],
        goal: Coord,
        enemy_specs: tuple[EnemySpec, ...] | None = None,
        trap_cells: tuple[Coord, ...] = (),
    ) -> SolveResult:
        solver = self.optimized_solver if self.uses_optimized_search(layout) else self.legacy_solver
        return solver.solve(
            layout,
            player_start,
            enemy_starts,
            goal,
            enemy_specs=enemy_specs,
            trap_cells=trap_cells,
        )
