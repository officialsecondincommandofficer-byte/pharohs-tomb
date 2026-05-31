from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from functools import lru_cache

from .grid import MazeLayout
from .movement import available_actions, resolve_player_action, resolve_player_transition
from .models import Coord, EnemySpec, GameState, SolveResult, ZoneSpawnerSpec
from .path_reconstruction import reconstruct_actions, reconstruct_cell_path
from .rules import GreedyChaserRules
from .search import breadth_first_search
from .solver_context import SolverContext, build_solver_context
from .solver_policy import SolverDispatchPolicy
from .solver_strategies import (
    STRATEGY_GOAL_ORDERED,
    GoalDistanceActionOrder,
    SolverSearchStrategy,
)

# Ownership split:
# - Python owns board solving, strategy/policy selection, generation heuristics, and export validation.
# - Godot owns loading exported boards, replaying stored solution actions, and runtime enemy movement during play.
# The production solver below is goal-ordered only. The standalone backup solver preserves the old legacy search path separately.

ACTION_DELTAS: dict[Coord, str] = {
    (1, 0): "right",
    (-1, 0): "left",
    (0, -1): "up",
    (0, 1): "down",
}


def _normalize_goal_cells(goal: Coord, goal_cells: tuple[Coord, ...] = ()) -> tuple[Coord, ...]:
    return tuple(dict.fromkeys(goal_cells or (goal,)))


@lru_cache(maxsize=None)
def _goal_distances(layout: MazeLayout, goals: tuple[Coord, ...]) -> dict[Coord, int]:
    queue: deque[Coord] = deque(goals)
    distances = {goal: 0 for goal in goals}

    while queue:
        cell = queue.popleft()
        next_distance = distances[cell] + 1
        for predecessor in _player_transition_predecessors(layout, cell):
            if predecessor in distances:
                continue
            distances[predecessor] = next_distance
            queue.append(predecessor)

    return distances


@lru_cache(maxsize=None)
def _shortest_layout_path(layout: MazeLayout, start: Coord, goals: tuple[Coord, ...]) -> tuple[str, ...] | None:
    if start in goals:
        return ()

    queue: deque[Coord] = deque([start])
    parents: dict[Coord, tuple[Coord | None, str | None]] = {start: (None, None)}

    while queue:
        cell = queue.popleft()
        for action in available_actions(layout, cell, include_skip=False):
            neighbor = resolve_player_transition(layout, cell, action).resolved_cell
            if neighbor == cell or neighbor in parents:
                continue
            parents[neighbor] = (cell, action)
            if neighbor in goals:
                return reconstruct_cell_path(neighbor, parents)
            queue.append(neighbor)

    return None


def _player_transition_predecessors(layout: MazeLayout, destination: Coord) -> tuple[Coord, ...]:
    predecessors: set[Coord] = set()

    if layout.teleport_destination(destination) is None:
        for neighbor in layout.neighbors(destination):
            if not layout.is_player_blocked(neighbor, destination):
                predecessors.add(neighbor)

    for pair in layout.teleport_pairs:
        source = None
        if pair.a == destination:
            source = pair.b
        elif pair.b == destination:
            source = pair.a
        if source is None:
            continue
        for neighbor in layout.neighbors(source):
            if not layout.is_player_blocked(neighbor, source):
                predecessors.add(neighbor)

    return tuple(predecessors)


def build_default_search_strategies() -> dict[str, SolverSearchStrategy]:
    return {
        STRATEGY_GOAL_ORDERED: SolverSearchStrategy(
            name=STRATEGY_GOAL_ORDERED,
            action_ordering=GoalDistanceActionOrder(),
            prune_self_loops=True,
        ),
    }


@dataclass(slots=True)
class BaseMazeSolver:
    rules: GreedyChaserRules = field(default_factory=GreedyChaserRules)

    def shortest_path_length_without_enemies(
        self,
        layout: MazeLayout,
        start: Coord,
        goal: Coord,
        goal_cells: tuple[Coord, ...] = (),
    ) -> int | None:
        return _goal_distances(layout, _normalize_goal_cells(goal, goal_cells)).get(start)

    def shortest_path_without_enemies(
        self,
        layout: MazeLayout,
        start: Coord,
        goal: Coord,
        goal_cells: tuple[Coord, ...] = (),
    ) -> tuple[str, ...] | None:
        return _shortest_layout_path(layout, start, _normalize_goal_cells(goal, goal_cells))

    def sequence_is_safe(
        self,
        layout: MazeLayout,
        player_start: Coord,
        enemy_starts: tuple[Coord | None, ...],
        actions: tuple[str, ...],
        goal: Coord,
        enemy_specs: tuple[EnemySpec, ...] = (),
        goal_cells: tuple[Coord, ...] = (),
        zone_spawners: tuple[ZoneSpawnerSpec, ...] = (),
        trap_cells: tuple[Coord, ...] = (),
    ) -> bool:
        context = self._build_context(
            layout,
            player_start,
            enemy_starts,
            goal,
            goal_cells=goal_cells,
            enemy_specs=enemy_specs,
            zone_spawners=zone_spawners,
            trap_cells=trap_cells,
        )
        state = context.initial_state

        for action in actions:
            state = self.rules.step_state(
                layout,
                state,
                action,
                context.enemy_specs,
                goal_cells=context.goal_cells,
                zone_spawners=context.zone_spawners,
            )
            if state is None:
                return False
            if state.player_position in context.trap_lookup:
                return False

        return state.player_position in context.goal_cells

    def _build_context(
        self,
        layout: MazeLayout,
        player_start: Coord,
        enemy_starts: tuple[Coord | None, ...],
        goal: Coord,
        goal_cells: tuple[Coord, ...] = (),
        enemy_specs: tuple[EnemySpec, ...] | None = None,
        zone_spawners: tuple[ZoneSpawnerSpec, ...] = (),
        trap_cells: tuple[Coord, ...] = (),
    ) -> SolverContext:
        return build_solver_context(
            self.rules,
            layout,
            player_start,
            enemy_starts,
            goal,
            goal_cells=goal_cells,
            enemy_specs=enemy_specs,
            zone_spawners=zone_spawners,
            trap_cells=trap_cells,
        )


@dataclass(slots=True)
class MazeSolver(BaseMazeSolver):
    dispatch_policy: SolverDispatchPolicy = field(default_factory=SolverDispatchPolicy)
    search_strategies: dict[str, SolverSearchStrategy] = field(default_factory=build_default_search_strategies)

    def solve(
        self,
        layout: MazeLayout,
        player_start: Coord,
        enemy_starts: tuple[Coord | None, ...],
        goal: Coord,
        goal_cells: tuple[Coord, ...] = (),
        enemy_specs: tuple[EnemySpec, ...] | None = None,
        zone_spawners: tuple[ZoneSpawnerSpec, ...] = (),
        trap_cells: tuple[Coord, ...] = (),
    ) -> SolveResult:
        strategy_name = self.dispatch_policy.search_strategy_name()
        return self.solve_with_strategy(
            strategy_name,
            layout,
            player_start,
            enemy_starts,
            goal,
            goal_cells=goal_cells,
            enemy_specs=enemy_specs,
            zone_spawners=zone_spawners,
            trap_cells=trap_cells,
        )

    def solve_with_strategy(
        self,
        strategy_name: str,
        layout: MazeLayout,
        player_start: Coord,
        enemy_starts: tuple[Coord | None, ...],
        goal: Coord,
        goal_cells: tuple[Coord, ...] = (),
        enemy_specs: tuple[EnemySpec, ...] | None = None,
        zone_spawners: tuple[ZoneSpawnerSpec, ...] = (),
        trap_cells: tuple[Coord, ...] = (),
    ) -> SolveResult:
        strategy = self.search_strategies[strategy_name]
        context = self._build_context(
            layout,
            player_start,
            enemy_starts,
            goal,
            goal_cells=goal_cells,
            enemy_specs=enemy_specs,
            zone_spawners=zone_spawners,
            trap_cells=trap_cells,
        )
        if player_start in context.goal_cells:
            return SolveResult(solvable=True, actions=())

        goal_distances = _goal_distances(layout, context.goal_cells) if strategy.name == STRATEGY_GOAL_ORDERED else None
        search_tree = breadth_first_search(
            initial_state=context.initial_state,
            available_actions=lambda state: self._available_actions(strategy, context, state, goal_distances),
            transition=lambda state, action: self._transition(strategy, context, state, action),
            is_goal=lambda state: state.player_position in context.goal_cells,
        )
        if search_tree is None:
            return SolveResult(solvable=False, actions=())
        return SolveResult(solvable=True, actions=reconstruct_actions(search_tree.goal_state, search_tree.parents))

    def _available_actions(
        self,
        strategy: SolverSearchStrategy,
        context: SolverContext,
        state: GameState,
        goal_distances: dict[Coord, int] | None,
    ) -> list[str]:
        available_actions = self.rules.available_actions(context.layout, state.player_position, include_skip=True)
        return strategy.action_ordering.order_actions(context, state, available_actions, goal_distances)

    def _transition(
        self,
        strategy: SolverSearchStrategy,
        context: SolverContext,
        state: GameState,
        action: str,
    ) -> GameState | None:
        next_state = self.rules.step_state(
            context.layout,
            state,
            action,
            context.enemy_specs,
            goal_cells=context.goal_cells,
            zone_spawners=context.zone_spawners,
        )
        if next_state is None or next_state.player_position in context.trap_lookup:
            return None
        if strategy.prune_self_loops and next_state == state:
            return None
        return next_state
