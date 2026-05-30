from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from .grid import MazeLayout, edge_sort_key
from .models import Coord, Edge, EnemySpec, EnemySpawn, MazeRecord
from .solver import MazeSolver


@dataclass(slots=True)
class MazeGenerator:
    solver: MazeSolver
    rng: random.Random
    enemy_specs: tuple[EnemySpec, ...] = (EnemySpec(),)
    trap_count: int = 0
    player_only_wall_count: int = 0
    enemy_only_wall_count: int = 0

    def uses_generation_prefilter(self, layout: MazeLayout) -> bool:
        return self.solver.dispatch_policy.uses_generation_prefilter(layout)

    def generate_batch(
        self,
        width: int,
        height: int,
        min_moves: int,
        target_count: int,
        iteration: int,
        additional_checks: bool,
        additional_check_threshold: int,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> list[MazeRecord]:
        generated: list[MazeRecord] = []
        seen_signatures: set[tuple] = set()
        all_edges = list(MazeLayout.build_all_edges(width, height))
        largest_solution = 0
        board_seed = 0
        layouts_examined = 0
        attempts = 0
        rejections = 0

        while len(generated) < target_count:
            walls_remaining = self._build_connected_wall_set(width, height, all_edges)
            if progress_callback is not None:
                progress_callback(
                    {
                        "event": "board_seed_started",
                        "board_seed": board_seed,
                        "walls_remaining": len(walls_remaining),
                        "generated_count": len(generated),
                        "layouts_examined": layouts_examined,
                        "attempts": attempts,
                        "rejections": rejections,
                        "largest_solution": largest_solution,
                    }
                )

            while len(walls_remaining) > max(width, height):
                layout = MazeLayout(width=width, height=height, walls=frozenset(walls_remaining))
                normalized_walls = tuple(sorted(layout.walls, key=edge_sort_key))
                checks_remaining = len(walls_remaining)
                layouts_examined += 1
                if progress_callback is not None:
                    progress_callback(
                        {
                            "event": "layout_started",
                            "board_seed": board_seed,
                            "layout_index": layouts_examined,
                            "walls_remaining": len(walls_remaining),
                            "checks_remaining": checks_remaining,
                            "generated_count": len(generated),
                            "attempts": attempts,
                            "rejections": rejections,
                            "largest_solution": largest_solution,
                        }
                    )

                while checks_remaining > 0:
                    checks_remaining -= 1
                    attempts += 1
                    if progress_callback is not None and attempts % 500 == 0:
                        progress_callback(
                            {
                                "event": "progress",
                                "board_seed": board_seed,
                                "layout_index": layouts_examined,
                                "walls_remaining": len(walls_remaining),
                                "checks_remaining": checks_remaining,
                                "generated_count": len(generated),
                                "attempts": attempts,
                                "rejections": rejections,
                                "largest_solution": largest_solution,
                            }
                        )
                    record = self._try_record(
                        layout=layout,
                        normalized_walls=normalized_walls,
                        min_moves=min_moves,
                        iteration=iteration,
                        board_seed=board_seed,
                    )
                    if record is None:
                        rejections += 1
                        continue
                    if record.signature() in seen_signatures:
                        rejections += 1
                        continue

                    seen_signatures.add(record.signature())
                    generated.append(record)
                    if progress_callback is not None:
                        progress_callback(
                            {
                                "event": "record_found",
                                "board_seed": board_seed,
                                "layout_index": layouts_examined,
                                "walls_remaining": len(walls_remaining),
                                "generated_count": len(generated),
                                "attempts": attempts,
                                "rejections": rejections,
                                "largest_solution": largest_solution,
                                "solution_total_steps": record.solution_total_steps,
                                "player_start": record.player_start,
                                "goal": record.goal,
                                "trap_count": len(record.trap_cells),
                            }
                        )
                    if record.solution_total_steps >= largest_solution:
                        largest_solution = record.solution_total_steps
                        if additional_checks and largest_solution >= additional_check_threshold:
                            checks_remaining += largest_solution * largest_solution
                            if progress_callback is not None:
                                progress_callback(
                                    {
                                        "event": "additional_checks_expanded",
                                        "board_seed": board_seed,
                                        "layout_index": layouts_examined,
                                        "generated_count": len(generated),
                                        "attempts": attempts,
                                        "rejections": rejections,
                                        "largest_solution": largest_solution,
                                        "checks_remaining": checks_remaining,
                                    }
                                )

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
        augmented_layout = self._augment_layout_with_actor_walls(layout)
        if augmented_layout is None:
            return None

        player_start, enemy_spawns, goal, trap_cells = self._sample_positions(augmented_layout)
        enemy_starts = tuple(enemy.cell for enemy in enemy_spawns)
        if self.uses_generation_prefilter(augmented_layout):
            shortest_length = self.solver.shortest_path_length_without_enemies(augmented_layout, player_start, goal)
            if shortest_length is not None and shortest_length < min_moves:
                shortest_path = self.solver.shortest_path_without_enemies(augmented_layout, player_start, goal)
                if shortest_path is not None and self.solver.sequence_is_safe(
                    augmented_layout,
                    player_start,
                    enemy_starts,
                    shortest_path,
                    goal,
                    enemy_specs=self.enemy_specs,
                    trap_cells=trap_cells,
                ):
                    return None

        result = self.solver.solve(
            augmented_layout,
            player_start,
            enemy_starts,
            goal,
            enemy_specs=self.enemy_specs,
            trap_cells=trap_cells,
        )
        if not result.solvable or result.total_steps < min_moves:
            return None

        return MazeRecord(
            width=augmented_layout.width,
            height=augmented_layout.height,
            walls=normalized_walls,
            player_only_walls=tuple(sorted(augmented_layout.player_only_walls, key=edge_sort_key)),
            enemy_only_walls=tuple(sorted(augmented_layout.enemy_only_walls, key=edge_sort_key)),
            trap_cells=trap_cells,
            player_start=player_start,
            enemy_spawns=enemy_spawns,
            goal=goal,
            solution=result.actions,
            iteration=iteration,
            seed_hint=board_seed,
        )

    def _augment_layout_with_actor_walls(self, layout: MazeLayout) -> MazeLayout | None:
        if self.player_only_wall_count <= 0 and self.enemy_only_wall_count <= 0:
            return layout

        available_edges = [
            edge for edge in MazeLayout.build_all_edges(layout.width, layout.height)
            if edge not in layout.walls
        ]
        if len(available_edges) < self.player_only_wall_count + self.enemy_only_wall_count:
            return None

        available_edges.sort(key=edge_sort_key)
        remaining_edges = list(available_edges)
        player_only_walls = self._sample_edge_subset(remaining_edges, self.player_only_wall_count)
        enemy_only_walls = self._sample_edge_subset(remaining_edges, self.enemy_only_wall_count)
        if player_only_walls is None or enemy_only_walls is None:
            return None

        return MazeLayout(
            width=layout.width,
            height=layout.height,
            walls=layout.walls,
            player_only_walls=frozenset(player_only_walls),
            enemy_only_walls=frozenset(enemy_only_walls),
            teleport_pairs=layout.teleport_pairs,
            enemy_teleport_pairs=layout.enemy_teleport_pairs,
            shared_teleport_pairs=layout.shared_teleport_pairs,
        )

    def _sample_edge_subset(self, remaining_edges: list[Edge], count: int) -> list[Edge] | None:
        if count <= 0:
            return []
        if len(remaining_edges) < count:
            return None

        selected_indices = sorted(self.rng.sample(range(len(remaining_edges)), count), reverse=True)
        selected_edges: list[Edge] = []
        for index in selected_indices:
            selected_edges.append(remaining_edges.pop(index))
        selected_edges.sort(key=edge_sort_key)
        return selected_edges
