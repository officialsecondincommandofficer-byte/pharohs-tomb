from __future__ import annotations

from dataclasses import dataclass

from .models import GameState, SolveResult
from .path_reconstruction import reconstruct_actions
from .search import breadth_first_search
from .solver import BaseMazeSolver
from .solver_context import SolverContext


@dataclass(slots=True)
class BackupMazeSolver(BaseMazeSolver):
    """Standalone rollback-safe copy of the legacy BFS solver behavior."""

    def solve(
        self,
        layout,
        player_start,
        enemy_starts,
        goal,
        enemy_specs=None,
        trap_cells=(),
    ):
        context = self._build_context(
            layout,
            player_start,
            enemy_starts,
            goal,
            enemy_specs=enemy_specs,
            trap_cells=trap_cells,
        )
        if player_start == goal:
            return SolveResult(solvable=True, actions=())

        search_tree = breadth_first_search(
            initial_state=context.initial_state,
            available_actions=lambda state: self.rules.available_actions(
                context.layout,
                state.player_position,
                include_skip=True,
            ),
            transition=lambda state, action: self._transition(context, state, action),
            is_goal=lambda state: state.player_position == context.goal,
        )
        if search_tree is None:
            return SolveResult(solvable=False, actions=())
        return SolveResult(solvable=True, actions=reconstruct_actions(search_tree.goal_state, search_tree.parents))

    def _transition(self, context: SolverContext, state: GameState, action: str) -> GameState | None:
        next_state = self.rules.step_state(context.layout, state, action, context.enemy_specs)
        if next_state is None or next_state.player_position in context.trap_lookup:
            return None
        return next_state
