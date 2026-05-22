from __future__ import annotations

import random
from dataclasses import dataclass

from .grid import MazeLayout, edge_sort_key
from .models import Coord, Edge, EnemySpec, EnemySpawn, MazeRecord
from .solver import MazeSolver


@dataclass(slots=True)
class MazeGenerator:
    solver: MazeSolver
    rng: random.Random
    enemy_specs: tuple[EnemySpec, ...] = (EnemySpec(),)

    def generate_batch(
        self,
        width: int,
        height: int,
        min_moves: int,
        target_count: int,
        iteration: int,
        additional_checks: bool,
        additional_check_threshold: int,
    ) -> list[MazeRecord]:
        generated: list[MazeRecord] = []
        seen_signatures: set[tuple] = set()
        all_edges = list(MazeLayout.build_all_edges(width, height))
        largest_solution = 0
        board_seed = 0

        while len(generated) < target_count:
            walls_remaining = self._build_connected_wall_set(width, height, all_edges)

            while len(walls_remaining) > max(width, height):
                checks_remaining = len(walls_remaining)

                while checks_remaining > 0:
                    checks_remaining -= 1
                    record = self._try_record(
                        width=width,
                        height=height,
                        walls_remaining=walls_remaining,
                        min_moves=min_moves,
                        iteration=iteration,
                        board_seed=board_seed,
                    )
                    if record is None:
                        continue
                    if record.signature() in seen_signatures:
                        continue

                    seen_signatures.add(record.signature())
                    generated.append(record)
                    if record.solution_total_steps >= largest_solution:
                        largest_solution = record.solution_total_steps
                        if additional_checks and largest_solution >= additional_check_threshold:
                            checks_remaining += largest_solution * largest_solution

                    if len(generated) >= target_count:
                        return generated

                walls_remaining.pop(self.rng.randrange(len(walls_remaining)))

            board_seed += 1

        return generated

    def _build_connected_wall_set(self, width: int, height: int, all_edges: list[Edge]) -> list[Edge]:
        walls_remaining = list(all_edges)
        minimum_open_edges = width * height

        for _ in range(minimum_open_edges):
            walls_remaining.pop(self.rng.randrange(len(walls_remaining)))

        while not MazeLayout(width=width, height=height, walls=frozenset(walls_remaining)).is_connected():
            walls_remaining.pop(self.rng.randrange(len(walls_remaining)))

        return walls_remaining

    def _sample_positions(self, layout: MazeLayout) -> tuple[Coord, tuple[EnemySpawn, ...], Coord]:
        while True:
            player_start = layout.random_cell(self.rng)
            goal = layout.random_cell(self.rng)
            if player_start == goal:
                continue

            occupied = {player_start, goal}
            enemy_spawns: list[EnemySpawn] = []
            for spec in self.enemy_specs:
                enemy_cell = self._sample_distinct_cell(layout, occupied)
                occupied.add(enemy_cell)
                enemy_spawns.append(EnemySpawn.from_spec(spec, enemy_cell))

            return player_start, tuple(enemy_spawns), goal

    def _sample_distinct_cell(self, layout: MazeLayout, occupied: set[Coord]) -> Coord:
        while True:
            cell = layout.random_cell(self.rng)
            if cell not in occupied:
                return cell

    def _try_record(
        self,
        width: int,
        height: int,
        walls_remaining: list[Edge],
        min_moves: int,
        iteration: int,
        board_seed: int,
    ) -> MazeRecord | None:
        layout = MazeLayout(width=width, height=height, walls=frozenset(walls_remaining))
        player_start, enemy_spawns, goal = self._sample_positions(layout)
        enemy_starts = tuple(enemy.cell for enemy in enemy_spawns)
        result = self.solver.solve(layout, player_start, enemy_starts, goal, enemy_specs=self.enemy_specs)
        if not result.solvable or result.total_steps < min_moves:
            return None

        normalized_walls = tuple(sorted(layout.walls, key=edge_sort_key))
        return MazeRecord(
            width=width,
            height=height,
            walls=normalized_walls,
            player_start=player_start,
            enemy_spawns=enemy_spawns,
            goal=goal,
            solution=result.actions,
            iteration=iteration,
            seed_hint=board_seed,
        )
