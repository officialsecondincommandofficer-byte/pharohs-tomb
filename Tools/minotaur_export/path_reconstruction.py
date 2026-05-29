from __future__ import annotations

from typing import TypeVar


StateT = TypeVar("StateT")
CellT = TypeVar("CellT")


def reconstruct_actions(
    goal_state: StateT,
    parents: dict[StateT, tuple[StateT | None, str | None]],
) -> tuple[str, ...]:
    actions: list[str] = []
    state: StateT | None = goal_state

    while state is not None:
        previous, action = parents[state]
        if action is not None:
            actions.append(action)
        state = previous

    actions.reverse()
    return tuple(actions)


def reconstruct_cell_path(
    goal: CellT,
    parents: dict[CellT, tuple[CellT | None, str | None]],
) -> tuple[str, ...]:
    return reconstruct_actions(goal, parents)
