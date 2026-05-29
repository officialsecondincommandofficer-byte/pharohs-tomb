from __future__ import annotations

from dataclasses import dataclass

from .grid import MazeLayout
from .solver_strategies import STRATEGY_GOAL_ORDERED


DEFAULT_PRIMARY_STRATEGY_NAME = STRATEGY_GOAL_ORDERED
DEFAULT_GENERATION_PREFILTER_MIN_DIMENSION = 13


@dataclass(frozen=True, slots=True)
class SolverDispatchPolicy:
    generation_prefilter_min_dimension: int = DEFAULT_GENERATION_PREFILTER_MIN_DIMENSION
    primary_strategy_name: str = DEFAULT_PRIMARY_STRATEGY_NAME

    def default_search_strategy_name(self) -> str:
        return self.primary_strategy_name

    def uses_generation_prefilter(self, layout: MazeLayout) -> bool:
        return max(layout.width, layout.height) >= self.generation_prefilter_min_dimension

    def search_strategy_name(self) -> str:
        return self.default_search_strategy_name()
