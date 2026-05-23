from __future__ import annotations

import sys
import unittest
import random
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from minotaur_export.exporter import GodotMazeExporter
from minotaur_export.generator import MazeGenerator
from minotaur_export.grid import MazeLayout, normalize_edge
from minotaur_export.models import EnemySpec, EnemySpawn, GameState, GenerationConfig, MazeRecord
from minotaur_export.rules import GreedyChaserRules
from minotaur_export.solver_backup import BackupMazeSolver
from minotaur_export.solver import LegacyMazeSolver, MazeSolver, OptimizedMazeSolver


class MazeSolverTests(unittest.TestCase):
    def test_solver_returns_empty_solution_when_player_starts_on_goal(self) -> None:
        layout = MazeLayout(width=2, height=2)
        result = MazeSolver().solve(layout, player_start=(0, 0), enemy_starts=((1, 1),), goal=(0, 0))
        self.assertTrue(result.solvable)
        self.assertEqual(result.actions, ())

    def test_solver_finds_solution_when_goal_is_protected_by_wall(self) -> None:
        layout = MazeLayout(
            width=2,
            height=2,
            walls=frozenset({normalize_edge((0, 1), (1, 1))}),
        )
        result = MazeSolver().solve(layout, player_start=(0, 0), enemy_starts=((1, 1),), goal=(0, 1))
        self.assertTrue(result.solvable)
        self.assertEqual(result.actions, ("down",))

    def test_solver_rejects_solution_when_any_enemy_catches_player(self) -> None:
        layout = MazeLayout(width=3, height=1)
        result = MazeSolver().solve(layout, player_start=(0, 0), enemy_starts=((2, 0),), goal=(1, 0))
        self.assertFalse(result.solvable)

    def test_solver_rejects_solution_when_player_must_step_on_trap(self) -> None:
        layout = MazeLayout(width=2, height=1)
        result = MazeSolver().solve(
            layout,
            player_start=(0, 0),
            enemy_starts=((0, 0),),
            goal=(1, 0),
            trap_cells=((1, 0),),
        )
        self.assertFalse(result.solvable)

    def test_shortest_layout_path_can_be_simulated_as_safe(self) -> None:
        layout = MazeLayout(
            width=2,
            height=2,
            walls=frozenset({normalize_edge((0, 1), (1, 1))}),
        )
        solver = MazeSolver()
        enemy_specs = (EnemySpec(move_priority="horizontal"),)
        shortest_path = solver.shortest_path_without_enemies(layout, start=(0, 0), goal=(0, 1))

        self.assertEqual(shortest_path, ("down",))
        self.assertTrue(
            solver.sequence_is_safe(
                layout,
                player_start=(0, 0),
                enemy_starts=((1, 1),),
                actions=shortest_path,
                goal=(0, 1),
                enemy_specs=enemy_specs,
            )
        )

    def test_solver_dispatches_to_legacy_for_12x12_and_smaller(self) -> None:
        solver = MazeSolver()

        self.assertFalse(solver.uses_optimized_search(MazeLayout(width=12, height=12)))
        self.assertFalse(solver.uses_optimized_search(MazeLayout(width=12, height=8)))
        self.assertTrue(solver.uses_optimized_search(MazeLayout(width=13, height=12)))
        self.assertIsInstance(solver.legacy_solver, LegacyMazeSolver)
        self.assertIsInstance(solver.optimized_solver, OptimizedMazeSolver)

    def test_backup_solver_matches_legacy_behavior(self) -> None:
        layout = MazeLayout(
            width=2,
            height=2,
            walls=frozenset({normalize_edge((0, 1), (1, 1))}),
        )

        legacy_result = LegacyMazeSolver().solve(
            layout,
            player_start=(0, 0),
            enemy_starts=((1, 1),),
            goal=(0, 1),
        )
        backup_result = BackupMazeSolver().solve(
            layout,
            player_start=(0, 0),
            enemy_starts=((1, 1),),
            goal=(0, 1),
        )

        self.assertEqual(backup_result, legacy_result)


class GreedyChaserRulesTests(unittest.TestCase):
    def test_horizontal_priority_moves_on_x_axis_first(self) -> None:
        layout = MazeLayout(width=3, height=3)
        rules = GreedyChaserRules(minotaur_steps=1, move_priority="horizontal")
        self.assertEqual(rules.move_enemy(layout, player_location=(2, 2), enemy_location=(0, 0)), (1, 0))

    def test_vertical_priority_moves_on_y_axis_first(self) -> None:
        layout = MazeLayout(width=3, height=3)
        rules = GreedyChaserRules(minotaur_steps=1, move_priority="vertical")
        self.assertEqual(rules.move_enemy(layout, player_location=(2, 2), enemy_location=(0, 0)), (0, 1))

    def test_multiple_enemies_block_each_other_sequentially(self) -> None:
        layout = MazeLayout(width=4, height=1)
        rules = GreedyChaserRules()
        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(3, 0),
                enemy_positions=((0, 0), (1, 0)),
            ),
            action="skip",
            enemy_specs=(EnemySpec(move_priority="horizontal", step_count=1), EnemySpec(move_priority="horizontal", step_count=1)),
        )
        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.enemy_positions, ((0, 0), (2, 0)))

    def test_earlier_killer_removes_later_enemy_and_skips_victim_turn(self) -> None:
        layout = MazeLayout(width=3, height=1)
        rules = GreedyChaserRules()
        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(2, 0),
                enemy_positions=((0, 0), (1, 0)),
            ),
            action="skip",
            enemy_specs=(
                EnemySpec(move_priority="horizontal", step_count=1, traits=("killer",)),
                EnemySpec(move_priority="horizontal", step_count=1),
            ),
        )
        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.enemy_positions, ((1, 0), None))

    def test_earlier_killer_removes_later_killer(self) -> None:
        layout = MazeLayout(width=3, height=1)
        rules = GreedyChaserRules()
        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(2, 0),
                enemy_positions=((0, 0), (1, 0)),
            ),
            action="skip",
            enemy_specs=(
                EnemySpec(move_priority="horizontal", step_count=1, traits=("killer",)),
                EnemySpec(move_priority="horizontal", step_count=1, traits=("killer",)),
            ),
        )
        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.enemy_positions, ((1, 0), None))

    def test_later_killer_dies_when_entering_earlier_killer(self) -> None:
        layout = MazeLayout(width=3, height=1, walls=frozenset({normalize_edge((0, 0), (1, 0))}))
        rules = GreedyChaserRules()
        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(0, 0),
                enemy_positions=((1, 0), (2, 0)),
            ),
            action="skip",
            enemy_specs=(
                EnemySpec(move_priority="horizontal", step_count=1, traits=("killer",)),
                EnemySpec(move_priority="horizontal", step_count=1, traits=("killer",)),
            ),
        )
        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.enemy_positions, ((1, 0), None))

    def test_later_killer_removes_earlier_non_killer(self) -> None:
        layout = MazeLayout(width=3, height=1, walls=frozenset({normalize_edge((0, 0), (1, 0))}))
        rules = GreedyChaserRules()
        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(0, 0),
                enemy_positions=((1, 0), (2, 0)),
            ),
            action="skip",
            enemy_specs=(
                EnemySpec(move_priority="horizontal", step_count=1),
                EnemySpec(move_priority="horizontal", step_count=1, traits=("killer",)),
            ),
        )
        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.enemy_positions, (None, (1, 0)))

    def test_non_killer_dies_when_entering_killer(self) -> None:
        layout = MazeLayout(width=3, height=1, walls=frozenset({normalize_edge((0, 0), (1, 0))}))
        rules = GreedyChaserRules()
        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(0, 0),
                enemy_positions=((1, 0), (2, 0)),
            ),
            action="skip",
            enemy_specs=(
                EnemySpec(move_priority="horizontal", step_count=1, traits=("killer",)),
                EnemySpec(move_priority="horizontal", step_count=1),
            ),
        )
        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.enemy_positions, ((1, 0), None))

    def test_killer_still_catches_player(self) -> None:
        layout = MazeLayout(width=3, height=1)
        rules = GreedyChaserRules()
        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(1, 0),
                enemy_positions=((2, 0),),
            ),
            action="skip",
            enemy_specs=(EnemySpec(move_priority="horizontal", step_count=1, traits=("killer",)),),
        )
        self.assertIsNone(next_state)

    def test_invalid_priority_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            GreedyChaserRules(move_priority="diagonal")


class MazeGeneratorTests(unittest.TestCase):
    def test_sample_positions_keeps_player_goal_and_enemies_distinct(self) -> None:
        generator = MazeGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
            enemy_specs=(EnemySpec(move_priority="horizontal"), EnemySpec(move_priority="vertical")),
        )
        player_start, enemy_spawns, goal, trap_cells = generator._sample_positions(MazeLayout(width=4, height=4))
        occupied = {player_start, goal}
        occupied.update(enemy.cell for enemy in enemy_spawns)
        occupied.update(trap_cells)

        self.assertEqual(len(enemy_spawns), 2)
        self.assertEqual(len(occupied), 4)
        self.assertEqual(enemy_spawns[0].move_priority, "horizontal")
        self.assertEqual(enemy_spawns[1].move_priority, "vertical")

    def test_sample_positions_includes_distinct_traps_when_requested(self) -> None:
        generator = MazeGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
            trap_count=2,
        )
        player_start, enemy_spawns, goal, trap_cells = generator._sample_positions(MazeLayout(width=4, height=4))

        self.assertEqual(len(trap_cells), 2)
        self.assertEqual(len(set(trap_cells)), 2)
        self.assertNotIn(player_start, trap_cells)
        self.assertNotIn(goal, trap_cells)
        self.assertTrue(all(enemy.cell not in trap_cells for enemy in enemy_spawns))

    def test_generation_config_marks_first_specs_as_killers(self) -> None:
        config = GenerationConfig(
            source_project=Path("."),
            output_dir=Path("."),
            greedy_horizontal_count=1,
            greedy_vertical_count=1,
            killer_count=1,
            trap_count=2,
        )

        specs = config.enemy_specs

        self.assertEqual(len(specs), 2)
        self.assertEqual(specs[0].traits, ("killer",))
        self.assertEqual(specs[1].traits, ())
        self.assertEqual(config.generation_profile_id, "greedy_enemies_1x_1y_1killer_2traps_9x9_batch")

    def test_try_record_rejects_safe_short_solution_before_full_solve(self) -> None:
        class FixedPositionGenerator(MazeGenerator):
            def _sample_positions(self, layout: MazeLayout) -> tuple[tuple[int, int], tuple[EnemySpawn, ...], tuple[int, int], tuple[tuple[int, int], ...]]:
                return (
                    (0, 0),
                    (EnemySpawn.from_spec(EnemySpec(move_priority="horizontal"), (1, 1)),),
                    (0, 1),
                    (),
                )

        generator = FixedPositionGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
            enemy_specs=(EnemySpec(move_priority="horizontal"),),
        )
        layout = MazeLayout(
            width=2,
            height=2,
            walls=frozenset({normalize_edge((0, 1), (1, 1))}),
        )
        normalized_walls = tuple(sorted(layout.walls))

        record = generator._try_record(
            layout=layout,
            normalized_walls=normalized_walls,
            min_moves=2,
            iteration=1,
            board_seed=0,
        )

        self.assertIsNone(record)

    def test_generator_only_uses_optimized_prefilter_above_12x12(self) -> None:
        generator = MazeGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
        )

        self.assertFalse(generator.uses_optimized_generation(MazeLayout(width=12, height=12)))
        self.assertFalse(generator.uses_optimized_generation(MazeLayout(width=12, height=9)))
        self.assertTrue(generator.uses_optimized_generation(MazeLayout(width=13, height=12)))


class GodotMazeExporterTests(unittest.TestCase):
    def test_serialize_writes_explicit_version_and_cell_size(self) -> None:
        exporter = GodotMazeExporter()
        record = MazeRecord(
            width=4,
            height=4,
            walls=(),
            trap_cells=((2, 2),),
            player_start=(0, 0),
            enemy_spawns=(EnemySpawn("greedy_chaser", (3, 3), "horizontal"),),
            goal=(1, 1),
            solution=("right", "down"),
            iteration=1,
        )

        serialized = exporter.serialize(
            record=record,
            saved_at_unix=123,
            difficulty_label="easy",
            index=1,
            generation_profile_id="profile",
            cell_size=24,
        )

        self.assertIn("version = 1", serialized)
        self.assertIn("cell_size = 24", serialized)
        self.assertIn("trap_cells = Array[Vector2i]([Vector2i(2, 2)])", serialized)
        self.assertIn("enemy_spawns = Array[Dictionary]", serialized)
        self.assertIn('minotaur_spawn = Vector2i(3, 3)', serialized)
        self.assertIn('generation_profile_id = "profile"', serialized)

    def test_serialize_writes_enemy_traits_when_present(self) -> None:
        exporter = GodotMazeExporter()
        record = MazeRecord(
            width=4,
            height=4,
            walls=(),
            trap_cells=(),
            player_start=(0, 0),
            enemy_spawns=(EnemySpawn("greedy_chaser", (3, 3), "horizontal", traits=("killer",)),),
            goal=(1, 1),
            solution=("right", "down"),
            iteration=1,
        )

        serialized = exporter.serialize(
            record=record,
            saved_at_unix=123,
            difficulty_label="easy",
            index=1,
            generation_profile_id="profile",
            cell_size=24,
        )

        self.assertIn('"traits": Array[String](["killer"])', serialized)


if __name__ == "__main__":
    unittest.main()
