from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .grid import MazeLayout
from .models import Coord


ACTION_OFFSETS: dict[str, Coord] = {
    "right": (1, 0),
    "left": (-1, 0),
    "up": (0, -1),
    "down": (0, 1),
}


@dataclass(frozen=True, slots=True)
class MoveResolution:
    stepped_cell: Coord
    resolved_cell: Coord
    used_teleport: bool


def available_actions(layout: MazeLayout, cell: Coord, include_skip: bool) -> list[str]:
    return list(_available_actions_cached(layout, cell, include_skip))


@lru_cache(maxsize=None)
def _available_actions_cached(layout: MazeLayout, cell: Coord, include_skip: bool) -> tuple[str, ...]:
    options: list[str] = ["skip"] if include_skip else []
    x, y = cell
    candidates = (
        ("right", (x + 1, y)),
        ("left", (x - 1, y)),
        ("up", (x, y - 1)),
        ("down", (x, y + 1)),
    )

    for action, nxt in candidates:
        if not layout.contains(nxt):
            continue
        if layout.is_blocked(cell, nxt):
            continue
        options.append(action)

    return tuple(options)


def apply_action(layout: MazeLayout, cell: Coord, action: str) -> Coord:
    return _apply_action_cached(layout, cell, action)


@lru_cache(maxsize=None)
def _apply_action_cached(layout: MazeLayout, cell: Coord, action: str) -> Coord:
    if action == "skip":
        return cell
    if action not in ACTION_OFFSETS:
        return cell

    x, y = cell
    dx, dy = ACTION_OFFSETS[action]
    nxt = (x + dx, y + dy)
    if not layout.contains(nxt):
        return cell
    if layout.is_blocked(cell, nxt):
        return cell
    return nxt


def resolve_player_action(layout: MazeLayout, cell: Coord, action: str) -> Coord:
    return resolve_player_transition(layout, cell, action).resolved_cell


def resolve_player_transition(layout: MazeLayout, cell: Coord, action: str) -> MoveResolution:
    stepped_cell = apply_action(layout, cell, action)
    teleport_destination = layout.teleport_destination(stepped_cell)
    if teleport_destination is not None:
        return MoveResolution(
            stepped_cell=stepped_cell,
            resolved_cell=teleport_destination,
            used_teleport=True,
        )

    return MoveResolution(
        stepped_cell=stepped_cell,
        resolved_cell=stepped_cell,
        used_teleport=False,
    )
