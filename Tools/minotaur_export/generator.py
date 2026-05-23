from __future__ import annotations

import random
from dataclasses import dataclass

from .grid import MazeLayout, edge_sort_key
from .models import Coord, Edge, EnemySpec, EnemySpawn, MazeRecord
from .solver import MazeSolver

OPTIMIZED_GENERATOR_MIN_DIMENSION = 13


@dataclass(slots=True)
class MazeGenerator:
    solver: MazeSolver
    rng: random.Random
    enemy_specs: tuple[EnemySpec, ...] = (EnemySpec(),)
    trap_count: int = 0

    def uses_optimized_generation(self, layout: MazeLayout) -> bool:
        return max(layout.width, layout.height) >= OPTIMIZED_GENERATOR_MIN_DIMENSION

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
                layout = MazeLayout(width=width, height=height, walls=frozenset(walls_remaining))
                normalized_walls = tuple(sorted(layout.walls, key=edge_sort_key))
                checks_remaining = len(walls_remaining)

                while checks_remaining > 0:
                    checks_remaining -= 1
                    record = self._try_record(
                        layout=layout,
                        normalized_walls=normalized_walls,
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

    def _sample_positions(self, layout: MazeLayout) -> tuple[Coord, tuple[EnemySpawn, ...], Coord, tuple[Coord, ...]]:
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

            trap_cells: list[Coord] = []
            for _ in range(self.trap_count):
                trap_cell = self._sample_distinct_cell(layout, occupied)
                occupied.add(trap_cell)
                trap_cells.append(trap_cell)

            return player_start, tuple(enemy_spawns), goal, tuple(sorted(trap_cells))

    def _sample_distinct_cell(self, layout: MazeLayout, occupied: set[Coord]) -> Coord:
        while True:
            cell = layout.random_cell(self.rng)
            if cell not in occupied:
                return cell

    def _try_record(
        self,
        layout: MazeLayout,
        normalized_walls: tuple[Edge, ...],
        min_moves: int,
        iteration: int,
        board_seed: int,
    ) -> MazeRecord | None:
        player_start, enemy_spawns, goal, trap_cells = self._sample_positions(layout)
        enemy_starts = tuple(enemy.cell for enemy in enemy_spawns)
        if self.uses_optimized_generation(layout):
            shortest_length = self.solver.shortest_path_length_without_enemies(layout, player_start, goal)
            if shortest_length is not None and shortest_length < min_moves:
                shortest_path = self.solver.shortest_path_without_enemies(layout, player_start, goal)
                if shortest_path is not None and self.solver.sequence_is_safe(
                    layout,
                    player_start,
                    enemy_starts,
                    shortest_path,
                    goal,
                    enemy_specs=self.enemy_specs,
                    trap_cells=trap_cells,
                ):
                    return None

        result = self.solver.solve(
            layout,
            player_start,
            enemy_starts,
            goal,
            enemy_specs=self.enemy_specs,
            trap_cells=trap_cells,
        )
        if not result.solvable or result.total_steps < min_moves:
            return None

        return MazeRecord(
            width=layout.width,
            height=layout.height,
            walls=normalized_walls,
            trap_cells=trap_cells,
            player_start=player_start,
            enemy_spawns=enemy_spawns,
            goal=goal,
            solution=result.actions,
            iteration=iteration,
            seed_hint=board_seed,
        )
