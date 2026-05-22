from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .grid import MazeLayout
from .models import Coord, EnemySpec, GameState, SolveResult
from .rules import GreedyChaserRules


@dataclass(slots=True)
class MazeSolver:
    rules: GreedyChaserRules = field(default_factory=GreedyChaserRules)

    def solve(
        self,
        layout: MazeLayout,
        player_start: Coord,
        enemy_starts: tuple[Coord, ...],
        goal: Coord,
        enemy_specs: tuple[EnemySpec, ...] | None = None,
        trap_cells: tuple[Coord, ...] = (),
    ) -> SolveResult:
        enemy_specs = enemy_specs or tuple(
            EnemySpec(move_priority=self.rules.move_priority, step_count=self.rules.minotaur_steps)
            for _ in enemy_starts
        )
        trap_lookup = set(trap_cells)
        initial_state = GameState(player_position=player_start, enemy_positions=enemy_starts)
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
