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
from minotaur_export.models import EnemyRuntimeState, EnemySpec, EnemySpawn, GameState, GenerationConfig, MazeRecord, TeleportPair
from minotaur_export.rules import GreedyChaserRules
from minotaur_export.solver_backup import BackupMazeSolver
from minotaur_export.solver import MazeSolver
from minotaur_export.solver_strategies import STRATEGY_GOAL_ORDERED


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

    def test_solver_uses_teleport_pairs_in_state_transitions(self) -> None:
        layout = MazeLayout(
            width=5,
            height=4,
            walls=frozenset(
                {
                    normalize_edge((1, 0), (2, 0)),
                    normalize_edge((1, 1), (2, 1)),
                    normalize_edge((1, 2), (2, 2)),
                    normalize_edge((1, 3), (2, 3)),
                }
            ),
            teleport_pairs=(TeleportPair((1, 3), (3, 0)),),
        )

        result = MazeSolver().solve(
            layout,
            player_start=(0, 0),
            enemy_starts=(),
            goal=(4, 0),
            enemy_specs=(),
        )

        self.assertTrue(result.solvable)
        self.assertEqual(result.actions, ("right", "down", "down", "down", "right"))

    def test_shortest_layout_path_uses_teleport_pairs(self) -> None:
        layout = MazeLayout(
            width=5,
            height=4,
            walls=frozenset(
                {
                    normalize_edge((1, 0), (2, 0)),
                    normalize_edge((1, 1), (2, 1)),
                    normalize_edge((1, 2), (2, 2)),
                    normalize_edge((1, 3), (2, 3)),
                }
            ),
            teleport_pairs=(TeleportPair((1, 3), (3, 0)),),
        )

        solver = MazeSolver()

        self.assertEqual(
            solver.shortest_path_without_enemies(layout, start=(0, 0), goal=(4, 0)),
            ("right", "down", "down", "down", "right"),
        )

    def test_solver_resolves_teleport_after_enemy_phase(self) -> None:
        layout = MazeLayout(
            width=3,
            height=1,
            teleport_pairs=(TeleportPair((1, 0), (2, 0)),),
        )

        result = MazeSolver().solve(
            layout,
            player_start=(0, 0),
            enemy_starts=((2, 0),),
            goal=(2, 0),
            enemy_specs=(EnemySpec(move_priority="horizontal", step_count=1),),
        )

        self.assertFalse(result.solvable)

    def test_solver_triggers_teleport_on_skip_when_waiting_on_portal(self) -> None:
        layout = MazeLayout(
            width=3,
            height=1,
            teleport_pairs=(TeleportPair((1, 0), (2, 0)),),
        )

        solver = MazeSolver()

        self.assertTrue(
            solver.sequence_is_safe(
                layout,
                player_start=(1, 0),
                enemy_starts=(),
                actions=("skip",),
                goal=(2, 0),
                enemy_specs=(),
            )
        )

    def test_enemy_only_teleport_is_used_by_enemy_but_not_player(self) -> None:
        layout = MazeLayout(
            width=4,
            height=1,
            enemy_teleport_pairs=(TeleportPair((1, 0), (3, 0)),),
        )
        rules = GreedyChaserRules(minotaur_steps=1, move_priority="horizontal")

        enemy_destination = rules.move_enemy(
            layout,
            player_location=(0, 0),
            enemy_location=(2, 0),
            move_priority="horizontal",
            step_count=1,
        )

        self.assertEqual(enemy_destination, (3, 0))
        self.assertEqual(rules.resolve_player_action(layout, (0, 0), "right"), (1, 0))

    def test_enemy_only_teleport_resolves_at_end_of_turn_not_mid_step(self) -> None:
        layout = MazeLayout(
            width=5,
            height=1,
            enemy_teleport_pairs=(TeleportPair((2, 0), (4, 0)),),
        )
        rules = GreedyChaserRules(minotaur_steps=2, move_priority="horizontal")

        enemy_destination = rules.move_enemy(
            layout,
            player_location=(0, 0),
            enemy_location=(3, 0),
            move_priority="horizontal",
            step_count=2,
        )

        self.assertEqual(enemy_destination, (1, 0))

    def test_shared_teleport_is_used_by_player_and_enemy_at_turn_end(self) -> None:
        layout = MazeLayout(
            width=4,
            height=1,
            shared_teleport_pairs=(TeleportPair((1, 0), (3, 0)),),
        )
        rules = GreedyChaserRules(minotaur_steps=1, move_priority="horizontal")

        self.assertEqual(rules.resolve_player_action(layout, (0, 0), "right"), (1, 0))
        player_state = GameState(player_position=(0, 0), enemy_positions=(), enemy_states=())
        next_state = rules.step_state(layout, player_state, "right", ())
        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.player_position, (3, 0))

        enemy_destination = rules.move_enemy(
            layout,
            player_location=(0, 0),
            enemy_location=(2, 0),
            move_priority="horizontal",
            step_count=1,
        )
        self.assertEqual(enemy_destination, (3, 0))

    def test_player_only_walls_allow_player_but_block_enemy(self) -> None:
        layout = MazeLayout(
            width=3,
            height=1,
            player_only_walls=frozenset({normalize_edge((1, 0), (2, 0))}),
        )
        rules = GreedyChaserRules(minotaur_steps=1, move_priority="horizontal")

        self.assertEqual(rules.resolve_player_action(layout, (1, 0), "right"), (2, 0))
        self.assertEqual(rules.move_enemy(layout, player_location=(0, 0), enemy_location=(2, 0), step_count=1), (2, 0))

    def test_enemy_only_walls_allow_enemy_but_block_player(self) -> None:
        layout = MazeLayout(
            width=3,
            height=1,
            enemy_only_walls=frozenset({normalize_edge((0, 0), (1, 0))}),
        )
        rules = GreedyChaserRules(minotaur_steps=1, move_priority="horizontal")

        self.assertEqual(rules.resolve_player_action(layout, (0, 0), "right"), (0, 0))
        self.assertEqual(rules.move_enemy(layout, player_location=(2, 0), enemy_location=(0, 0), step_count=1), (1, 0))

    def test_solver_uses_enemy_only_wall_in_pathfinding(self) -> None:
        layout = MazeLayout(
            width=3,
            height=2,
            enemy_only_walls=frozenset({normalize_edge((1, 0), (2, 0))}),
        )

        result = MazeSolver().solve(
            layout,
            player_start=(0, 0),
            enemy_starts=(),
            goal=(2, 0),
            enemy_specs=(),
        )

        self.assertTrue(result.solvable)
        self.assertEqual(result.actions, ("right", "down", "right", "up"))

    def test_solver_uses_player_only_wall_as_escape_barrier(self) -> None:
        layout = MazeLayout(
            width=4,
            height=1,
            player_only_walls=frozenset({normalize_edge((1, 0), (2, 0))}),
        )

        result = MazeSolver().solve(
            layout,
            player_start=(1, 0),
            enemy_starts=((0, 0),),
            goal=(3, 0),
            enemy_specs=(EnemySpec(move_priority="horizontal", step_count=2),),
        )

        self.assertTrue(result.solvable)
        self.assertEqual(result.actions, ("right", "right"))

    def test_solver_defaults_to_goal_ordered_strategy(self) -> None:
        solver = MazeSolver()

        self.assertEqual(solver.dispatch_policy.primary_strategy_name, STRATEGY_GOAL_ORDERED)
        self.assertEqual(solver.dispatch_policy.default_search_strategy_name(), STRATEGY_GOAL_ORDERED)
        self.assertEqual(solver.dispatch_policy.search_strategy_name(), STRATEGY_GOAL_ORDERED)

    def test_backup_solver_matches_legacy_strategy_behavior(self) -> None:
        backup_solver = BackupMazeSolver()
        cases = [
            (
                MazeLayout(
                    width=2,
                    height=2,
                    walls=frozenset({normalize_edge((0, 1), (1, 1))}),
                ),
                (0, 0),
                ((1, 1),),
                (0, 1),
                (),
            ),
            (
                MazeLayout(width=3, height=1),
                (0, 0),
                ((2, 0),),
                (1, 0),
                (),
            ),
            (
                MazeLayout(width=3, height=2),
                (0, 0),
                ((2, 1),),
                (2, 0),
                ((1, 0),),
            ),
        ]

        for layout, player_start, enemy_starts, goal, trap_cells in cases:
            with self.subTest(layout=layout, player_start=player_start, enemy_starts=enemy_starts, goal=goal):
                backup_result = backup_solver.solve(
                    layout,
                    player_start=player_start,
                    enemy_starts=enemy_starts,
                    goal=goal,
                    trap_cells=trap_cells,
                )
                if backup_result.solvable:
                    self.assertTrue(
                        backup_solver.sequence_is_safe(
                            layout,
                            player_start=player_start,
                            enemy_starts=enemy_starts,
                            actions=backup_result.actions,
                            goal=goal,
                            enemy_specs=(EnemySpec(move_priority="horizontal"),) * len(enemy_starts),
                            trap_cells=trap_cells,
                        )
                    )

    def test_goal_ordered_strategy_matches_backup_solver_on_shared_subset_cases(self) -> None:
        solver = MazeSolver()
        backup_solver = BackupMazeSolver()
        cases = [
            (
                MazeLayout(width=3, height=3),
                (0, 0),
                ((2, 2),),
                (2, 0),
            ),
            (
                MazeLayout(
                    width=4,
                    height=3,
                    walls=frozenset(
                        {
                            normalize_edge((1, 0), (1, 1)),
                            normalize_edge((1, 1), (2, 1)),
                        }
                    ),
                ),
                (0, 0),
                ((3, 2),),
                (3, 0),
            ),
            (
                MazeLayout(
                    width=5,
                    height=4,
                    walls=frozenset(
                        {
                            normalize_edge((1, 0), (2, 0)),
                            normalize_edge((2, 1), (2, 2)),
                            normalize_edge((3, 2), (4, 2)),
                        }
                    ),
                ),
                (0, 3),
                ((4, 0),),
                (4, 3),
            ),
        ]

        for layout, player_start, enemy_starts, goal in cases:
            with self.subTest(layout=layout, player_start=player_start, enemy_starts=enemy_starts, goal=goal):
                backup_result = backup_solver.solve(
                    layout,
                    player_start=player_start,
                    enemy_starts=enemy_starts,
                    goal=goal,
                )
                goal_ordered_result = solver.solve(
                    layout,
                    player_start=player_start,
                    enemy_starts=enemy_starts,
                    goal=goal,
                )
                self.assertEqual(goal_ordered_result.solvable, backup_result.solvable)
                if goal_ordered_result.solvable:
                    self.assertTrue(
                        solver.sequence_is_safe(
                            layout,
                            player_start=player_start,
                            enemy_starts=enemy_starts,
                            actions=goal_ordered_result.actions,
                            goal=goal,
                            enemy_specs=(EnemySpec(move_priority="horizontal"),) * len(enemy_starts),
                        )
                    )



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

    def test_player_loses_if_enemy_still_occupies_destination_after_enemy_phase(self) -> None:
        layout = MazeLayout(width=5, height=5)
        rules = GreedyChaserRules()
        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(4, 4),
                enemy_positions=((4, 3),),
                enemy_states=(EnemyRuntimeState(),),
            ),
            action="up",
            enemy_specs=(EnemySpec(move_priority="horizontal", step_count=2),),
        )
        self.assertIsNone(next_state)

    def test_samurai_rotates_then_begins_charge_when_player_is_seen(self) -> None:
        layout = MazeLayout(width=4, height=4)
        rules = GreedyChaserRules()
        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(2, 0),
                enemy_positions=((0, 0),),
                enemy_states=(EnemyRuntimeState(facing_index=0),),
            ),
            action="skip",
            enemy_specs=(EnemySpec(enemy_type="samurai"),),
        )
        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.enemy_positions, ((0, 0),))
        self.assertEqual(next_state.enemy_states[0], EnemyRuntimeState(facing_index=1, attack_phase=0, turns_until_dash=3))

    def test_samurai_dashes_after_countdown_and_ignores_walls(self) -> None:
        layout = MazeLayout(width=6, height=6, walls=frozenset({normalize_edge((0, 0), (0, 1))}))
        rules = GreedyChaserRules()
        state = GameState(
            player_position=(2, 5),
            enemy_positions=((2, 0),),
            enemy_states=(EnemyRuntimeState(facing_index=2, attack_phase=0, turns_until_dash=1),),
        )
        next_state = rules.step_state(
            layout,
            state=state,
            action="skip",
            enemy_specs=(EnemySpec(enemy_type="samurai"),),
        )
        self.assertIsNone(next_state)


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
            samurai_count=1,
            player_only_wall_count=2,
            enemy_only_wall_count=1,
        )

        specs = config.enemy_specs

        self.assertEqual(len(specs), 3)
        self.assertEqual(specs[0].traits, ("killer",))
        self.assertEqual(specs[1].traits, ())
        self.assertEqual(specs[2].enemy_type, "samurai")
        self.assertEqual(
            config.generation_profile_id,
            "greedy_enemies_1x_1y_1samurai_1killer_2traps_2playerwalls_1enemywalls_9x9_batch",
        )

    def test_actor_specific_walls_are_added_after_shared_layout_generation(self) -> None:
        generator = MazeGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
            enemy_specs=(),
            player_only_wall_count=1,
            enemy_only_wall_count=1,
        )
        layout = MazeLayout(
            width=3,
            height=2,
            walls=frozenset({normalize_edge((0, 0), (1, 0))}),
        )

        augmented_layout = generator._augment_layout_with_actor_walls(layout)

        self.assertIsNotNone(augmented_layout)
        self.assertEqual(augmented_layout.walls, layout.walls)
        self.assertEqual(len(augmented_layout.player_only_walls), 1)
        self.assertEqual(len(augmented_layout.enemy_only_walls), 1)
        self.assertTrue(augmented_layout.player_only_walls.isdisjoint(augmented_layout.enemy_only_walls))
        self.assertTrue(augmented_layout.player_only_walls.isdisjoint(layout.walls))
        self.assertTrue(augmented_layout.enemy_only_walls.isdisjoint(layout.walls))

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

    def test_generator_only_uses_generation_prefilter_above_12x12(self) -> None:
        generator = MazeGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
        )

        self.assertFalse(generator.uses_generation_prefilter(MazeLayout(width=12, height=12)))
        self.assertFalse(generator.uses_generation_prefilter(MazeLayout(width=12, height=9)))
        self.assertTrue(generator.uses_generation_prefilter(MazeLayout(width=13, height=12)))


class GodotMazeExporterTests(unittest.TestCase):
    def test_serialize_writes_explicit_version_and_cell_size(self) -> None:
        exporter = GodotMazeExporter()
        record = MazeRecord(
            width=4,
            height=4,
            walls=(),
            teleport_pairs=(),
            enemy_teleport_pairs=(),
            shared_teleport_pairs=(),
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
            teleport_pairs=(),
            enemy_teleport_pairs=(),
            shared_teleport_pairs=(),
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

    def test_serialize_writes_enemy_facing_index(self) -> None:
        exporter = GodotMazeExporter()
        record = MazeRecord(
            width=4,
            height=4,
            walls=(),
            teleport_pairs=(),
            enemy_teleport_pairs=(),
            shared_teleport_pairs=(),
            trap_cells=(),
            player_start=(0, 0),
            enemy_spawns=(EnemySpawn("samurai", (3, 3), "horizontal", facing_index=1),),
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

        self.assertIn('"facing_index": 1', serialized)

    def test_serialize_writes_teleport_pairs(self) -> None:
        exporter = GodotMazeExporter()
        record = MazeRecord(
            width=5,
            height=4,
            walls=(),
            teleport_pairs=(TeleportPair((1, 3), (3, 0)),),
            enemy_teleport_pairs=(),
            shared_teleport_pairs=(),
            trap_cells=(),
            player_start=(0, 0),
            enemy_spawns=(),
            goal=(4, 0),
            solution=("right", "down", "down", "down", "right"),
            iteration=1,
        )

        serialized = exporter.serialize(
            record=record,
            saved_at_unix=123,
            difficulty_label="probe",
            index=1,
            generation_profile_id="teleport_probe",
            cell_size=16,
        )

        self.assertIn('teleport_pairs = Array[Dictionary]([{"a": Vector2i(1, 3), "b": Vector2i(3, 0)}])', serialized)

    def test_serialize_writes_enemy_teleport_pairs(self) -> None:
        exporter = GodotMazeExporter()
        record = MazeRecord(
            width=4,
            height=1,
            walls=(),
            teleport_pairs=(),
            enemy_teleport_pairs=(TeleportPair((1, 0), (3, 0)),),
            shared_teleport_pairs=(),
            trap_cells=(),
            player_start=(0, 0),
            enemy_spawns=(EnemySpawn("greedy_chaser", (2, 0), "horizontal"),),
            goal=(0, 0),
            solution=(),
            iteration=1,
        )

        serialized = exporter.serialize(
            record=record,
            saved_at_unix=123,
            difficulty_label="probe",
            index=1,
            generation_profile_id="enemy_teleport_probe",
            cell_size=16,
        )

        self.assertIn('enemy_teleport_pairs = Array[Dictionary]([{"a": Vector2i(1, 0), "b": Vector2i(3, 0)}])', serialized)

    def test_serialize_writes_shared_teleport_pairs(self) -> None:
        exporter = GodotMazeExporter()
        record = MazeRecord(
            width=4,
            height=1,
            walls=(),
            teleport_pairs=(),
            enemy_teleport_pairs=(),
            shared_teleport_pairs=(TeleportPair((1, 0), (3, 0)),),
            trap_cells=(),
            player_start=(0, 0),
            enemy_spawns=(),
            goal=(0, 0),
            solution=(),
            iteration=1,
        )

        serialized = exporter.serialize(
            record=record,
            saved_at_unix=123,
            difficulty_label="probe",
            index=1,
            generation_profile_id="shared_teleport_probe",
            cell_size=16,
        )

        self.assertIn('shared_teleport_pairs = Array[Dictionary]([{"a": Vector2i(1, 0), "b": Vector2i(3, 0)}])', serialized)

    def test_serialize_writes_actor_specific_wall_layers(self) -> None:
        exporter = GodotMazeExporter()
        record = MazeRecord(
            width=4,
            height=2,
            walls=(),
            player_only_walls=(normalize_edge((0, 0), (1, 0)),),
            enemy_only_walls=(normalize_edge((2, 0), (2, 1)),),
            teleport_pairs=(),
            enemy_teleport_pairs=(),
            shared_teleport_pairs=(),
            trap_cells=(),
            player_start=(0, 0),
            enemy_spawns=(),
            goal=(3, 1),
            solution=("right",),
            iteration=1,
        )

        serialized = exporter.serialize(
            record=record,
            saved_at_unix=123,
            difficulty_label="probe",
            index=1,
            generation_profile_id="actor_wall_probe",
            cell_size=16,
        )

        self.assertIn("player_vertical_walls = Array[Vector2i]([Vector2i(1, 0)])", serialized)
        self.assertIn("enemy_horizontal_walls = Array[Vector2i]([Vector2i(2, 1)])", serialized)


if __name__ == "__main__":
    unittest.main()
