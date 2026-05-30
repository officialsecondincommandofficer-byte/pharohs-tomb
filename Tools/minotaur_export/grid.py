from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable

from .models import Coord, Edge, TeleportPair


def normalize_edge(a: Coord, b: Coord) -> Edge:
    return (a, b) if a <= b else (b, a)


def edge_sort_key(edge: Edge) -> tuple[int, int, int, int]:
    (ax, ay), (bx, by) = edge
    return (ay, ax, by, bx)


def partition_walls(walls: Iterable[Edge]) -> tuple[list[Coord], list[Coord]]:
    horizontal: list[Coord] = []
    vertical: list[Coord] = []
    for a, b in walls:
        if a[0] != b[0]:
            vertical.append((max(a[0], b[0]), a[1]))
        else:
            horizontal.append((a[0], max(a[1], b[1])))

    horizontal.sort(key=lambda item: (item[1], item[0]))
    vertical.sort(key=lambda item: (item[1], item[0]))
    return horizontal, vertical


@dataclass(frozen=True, slots=True)
class MazeLayout:
    width: int
    height: int
    walls: frozenset[Edge] = field(default_factory=frozenset)
    player_only_walls: frozenset[Edge] = field(default_factory=frozenset)
    enemy_only_walls: frozenset[Edge] = field(default_factory=frozenset)
    teleport_pairs: tuple[TeleportPair, ...] = field(default_factory=tuple)
    enemy_teleport_pairs: tuple[TeleportPair, ...] = field(default_factory=tuple)
    shared_teleport_pairs: tuple[TeleportPair, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        normalized = frozenset(normalize_edge(a, b) for a, b in self.walls)
        normalized_player_only = frozenset(normalize_edge(a, b) for a, b in self.player_only_walls)
        normalized_enemy_only = frozenset(normalize_edge(a, b) for a, b in self.enemy_only_walls)
        normalized_teleports = tuple(
            sorted((pair.normalized() for pair in self.teleport_pairs), key=lambda pair: (pair.a[1], pair.a[0], pair.b[1], pair.b[0]))
        )
        normalized_enemy_teleports = tuple(
            sorted((pair.normalized() for pair in self.enemy_teleport_pairs), key=lambda pair: (pair.a[1], pair.a[0], pair.b[1], pair.b[0]))
        )
        normalized_shared_teleports = tuple(
            sorted((pair.normalized() for pair in self.shared_teleport_pairs), key=lambda pair: (pair.a[1], pair.a[0], pair.b[1], pair.b[0]))
        )
        object.__setattr__(self, "walls", normalized)
        object.__setattr__(self, "player_only_walls", normalized_player_only)
        object.__setattr__(self, "enemy_only_walls", normalized_enemy_only)
        object.__setattr__(self, "teleport_pairs", normalized_teleports)
        object.__setattr__(self, "enemy_teleport_pairs", normalized_enemy_teleports)
        object.__setattr__(self, "shared_teleport_pairs", normalized_shared_teleports)

    @staticmethod
    def build_all_edges(width: int, height: int) -> tuple[Edge, ...]:
        edges: list[Edge] = []
        for y in range(height):
            for x in range(width):
                if x + 1 < width:
                    edges.append(normalize_edge((x, y), (x + 1, y)))
                if y + 1 < height:
                    edges.append(normalize_edge((x, y), (x, y + 1)))
        return tuple(edges)

    def random_cell(self, rng: random.Random) -> Coord:
        return (rng.randrange(self.width), rng.randrange(self.height))

    def contains(self, cell: Coord) -> bool:
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height

    def neighbors(self, cell: Coord) -> Iterable[Coord]:
        x, y = cell
        if x > 0:
            yield (x - 1, y)
        if x + 1 < self.width:
            yield (x + 1, y)
        if y > 0:
            yield (x, y - 1)
        if y + 1 < self.height:
            yield (x, y + 1)

    def is_blocked(self, a: Coord, b: Coord) -> bool:
        return normalize_edge(a, b) in self.walls

    def is_player_blocked(self, a: Coord, b: Coord) -> bool:
        edge = normalize_edge(a, b)
        return edge in self.walls or edge in self.enemy_only_walls

    def is_enemy_blocked(self, a: Coord, b: Coord) -> bool:
        edge = normalize_edge(a, b)
        return edge in self.walls or edge in self.player_only_walls

    def teleport_destination(self, cell: Coord) -> Coord | None:
        return self._teleport_destination_from_pairs(cell, self.teleport_pairs)

    def enemy_teleport_destination(self, cell: Coord) -> Coord | None:
        return self._teleport_destination_from_pairs(cell, self.enemy_teleport_pairs)

    def shared_teleport_destination(self, cell: Coord) -> Coord | None:
        return self._teleport_destination_from_pairs(cell, self.shared_teleport_pairs)

    @staticmethod
    def _teleport_destination_from_pairs(cell: Coord, pairs: tuple[TeleportPair, ...]) -> Coord | None:
        for pair in pairs:
            if pair.a == cell:
                return pair.b
            if pair.b == cell:
                return pair.a
        return None

    def is_connected(self) -> bool:
        start = (0, 0)
        queue: deque[Coord] = deque([start])
        visited = {start}

        while queue:
            current = queue.popleft()
            for nxt in self.neighbors(current):
                if self.is_blocked(current, nxt) or nxt in visited:
                    continue
                visited.add(nxt)
                queue.append(nxt)

        return len(visited) == self.width * self.height
