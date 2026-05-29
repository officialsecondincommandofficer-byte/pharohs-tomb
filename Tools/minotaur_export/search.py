from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Generic, Iterable, TypeVar


StateT = TypeVar("StateT")


@dataclass(slots=True)
class SearchTree(Generic[StateT]):
    goal_state: StateT
    parents: dict[StateT, tuple[StateT | None, str | None]]


def breadth_first_search(
    initial_state: StateT,
    available_actions: Callable[[StateT], Iterable[str]],
    transition: Callable[[StateT, str], StateT | None],
    is_goal: Callable[[StateT], bool],
) -> SearchTree[StateT] | None:
    queue: deque[StateT] = deque([initial_state])
    parents: dict[StateT, tuple[StateT | None, str | None]] = {initial_state: (None, None)}

    while queue:
        state = queue.popleft()
        for action in available_actions(state):
            next_state = transition(state, action)
            if next_state is None or next_state in parents:
                continue

            parents[next_state] = (state, action)
            if is_goal(next_state):
                return SearchTree(goal_state=next_state, parents=parents)
            queue.append(next_state)

    return None
