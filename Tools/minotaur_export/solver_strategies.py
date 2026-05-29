from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import Coord, GameState
from .solver_context import SolverContext

STRATEGY_LEGACY = "legacy"
STRATEGY_GOAL_ORDERED = "goal_ordered"


class ActionOrderingStrategy(Protocol):
    def order_actions(
        self,
        context: SolverContext,
        state: GameState,
        available_actions: list[str],
        goal_distances: dict[Coord, int] | None,
    ) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class PreserveActionOrder:
    def order_actions(
        self,
        context: SolverContext,
        state: GameState,
        available_actions: list[str],
        goal_distances: dict[Coord, int] | None,
    ) -> list[str]:
        return available_actions


@dataclass(frozen=True, slots=True)
class GoalDistanceActionOrder:
    def order_actions(
        self,
        context: SolverContext,
        state: GameState,
        available_actions: list[str],
        goal_distances: dict[Coord, int] | None,
    ) -> list[str]:
        if goal_distances is None:
            return available_actions

        return sorted(
            available_actions,
            key=lambda action: (
                goal_distances.get(
                    context.rules.apply_action(context.layout, state.player_position, action),
                    float("inf"),
                ),
                1 if action == "skip" else 0,
            ),
        )


@dataclass(frozen=True, slots=True)
class SolverSearchStrategy:
    name: str
    action_ordering: ActionOrderingStrategy
    prune_self_loops: bool = False
