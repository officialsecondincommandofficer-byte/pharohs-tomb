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
from minotaur_export.models import (
    EnemyRuntimeState,
    EnemySpec,
    EnemySpawn,
    GameState,
    GenerationConfig,
    MazeRecord,
    PatrollerBehaviorState,
    SamuraiBehaviorState,
    TeleportPair,
    WandererBehaviorState,
    ZoneSpawnerSpec,
    ZoneSpawnerState,
)
from minotaur_export.enemy_contact_rules import CONTACT_TARGET_DIES, resolve_enemy_contact
from minotaur_export.enemy_turn_rules import EnemyTurnRules
from minotaur_export.rules import GreedyChaserRules
from minotaur_export.shared_enemy_schema import build_enemy_bridge_payload
from minotaur_export.solver_backup import BackupMazeSolver
from minotaur_export.solver import MazeSolver
from minotaur_export.solver_strategies import STRATEGY_GOAL_ORDERED


class MazeSolverTests(unittest.TestCase):
    def test_bridge_payload_resolves_components_for_legacy_greedy_enemy(self) -> None:
        payload = build_enemy_bridge_payload(
            enemy_type="greedy_chaser",
            move_priority="vertical",
            traits=("killer",),
            step_count=2,
        )

        self.assertEqual(payload["canonical_enemy_type"], "greedy_chaser")
        self.assertEqual(payload["archetype_id"], "enemy.greedy_chaser.vertical")
        self.assertEqual(payload["legacy"]["role"], "y_chaser")
        self.assertEqual(payload["legacy"]["movement_type"], "greedy")
        self.assertEqual(payload["components"]["movement"]["axis"], "vertical")
        self.assertEqual(payload["components"]["contact"]["enemy_collision"], "kill_non_killers")

    def test_bridge_payload_preserves_escape_linked_trait_compatibility(self) -> None:
        payload = build_enemy_bridge_payload(
            enemy_type="astar_chaser",
            traits=("escape_linked",),
            step_count=2,
        )

        self.assertEqual(payload["canonical_enemy_type"], "linked_escape_hunter")
        self.assertEqual(payload["legacy"]["role"], "linked_escape_hunter")
        self.assertEqual(payload["legacy"]["movement_type"], "astar")
        self.assertEqual(payload["components"]["spawn_context"]["kind"], "escape_zone_linked")

    def test_component_movement_family_drives_behavior_selection(self) -> None:
        rules = EnemyTurnRules()
        greedy_spec = EnemySpec(
            enemy_type="greedy_chaser",
            movement_type="greedy",
            patrol_route=((0, 0), (1, 0), (2, 0)),
            patrol_mode="loop",
        )
        patrol_spec = EnemySpec(
            enemy_type="patroller",
            patrol_route=((0, 0), (1, 0), (2, 0)),
            patrol_mode="loop",
        )

        self.assertEqual(type(rules.behavior_for_spec(greedy_spec)).__name__, "GreedyChaserBehavior")
        self.assertEqual(type(rules.behavior_for_spec(patrol_spec)).__name__, "PatrollerBehavior")

    def test_component_contact_rules_preserve_killer_behavior_without_trait_branching(self) -> None:
        killer_spec = EnemySpec(enemy_type="greedy_chaser", traits=("killer",))
        target_spec = EnemySpec(enemy_type="greedy_chaser")

        self.assertEqual(resolve_enemy_contact(0, 1, (killer_spec, target_spec)), CONTACT_TARGET_DIES)

    def test_solver_accepts_main_exit_win_on_dual_exit_board(self) -> None:
        layout = MazeLayout(width=4, height=4)
        win_zone_cells = ((3, 0), (2, 2), (3, 2), (2, 3), (3, 3))

        result = MazeSolver().solve(
            layout,
            player_start=(0, 0),
            enemy_starts=(),
            goal=(3, 0),
            goal_cells=win_zone_cells,
            enemy_specs=(),
        )

        self.assertTrue(result.solvable)
        self.assertEqual(result.actions, ("right", "right", "right"))

    def test_solver_accepts_escape_zone_win_on_dual_exit_board(self) -> None:
        layout = MazeLayout(width=4, height=4)
        win_zone_cells = ((3, 0), (0, 1), (1, 1), (0, 2), (1, 2))

        result = MazeSolver().solve(
            layout,
            player_start=(0, 0),
            enemy_starts=(),
            goal=(3, 0),
            goal_cells=win_zone_cells,
            enemy_specs=(),
        )

        self.assertTrue(result.solvable)
        self.assertEqual(result.actions, ("down",))

    def test_solver_returns_empty_solution_when_player_starts_on_goal(self) -> None:
        layout = MazeLayout(width=3, height=3)
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

    def test_one_way_passage_blocks_reverse_direction_for_player_and_enemy(self) -> None:
        layout = MazeLayout(
            width=3,
            height=1,
            one_way_passages=frozenset({((1, 0), (0, 0))}),
        )
        rules = GreedyChaserRules(minotaur_steps=1, move_priority="horizontal")

        self.assertEqual(rules.resolve_player_action(layout, (0, 0), "right"), (0, 0))
        self.assertEqual(rules.resolve_player_action(layout, (1, 0), "left"), (0, 0))
        self.assertEqual(rules.move_enemy(layout, player_location=(2, 0), enemy_location=(0, 0), step_count=1), (0, 0))

    def test_one_way_passage_updates_shortest_path_and_goal_distances(self) -> None:
        layout = MazeLayout(
            width=3,
            height=2,
            one_way_passages=frozenset({((2, 0), (1, 0))}),
        )
        solver = MazeSolver()

        self.assertEqual(solver.shortest_path_length_without_enemies(layout, start=(0, 0), goal=(2, 0)), 4)
        self.assertEqual(
            solver.shortest_path_without_enemies(layout, start=(0, 0), goal=(2, 0)),
            ("right", "down", "right", "up"),
        )

        result = solver.solve(
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
    def test_step_state_resolves_enemy_phase_before_shared_turn_end_teleport(self) -> None:
        layout = MazeLayout(
            width=4,
            height=1,
            shared_teleport_pairs=(TeleportPair((1, 0), (3, 0)),),
        )
        rules = GreedyChaserRules()

        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(0, 0),
                enemy_positions=((2, 0),),
            ),
            action="right",
            enemy_specs=(EnemySpec(move_priority="horizontal", step_count=1),),
        )

        self.assertIsNone(next_state)

    def test_blocked_escape_zone_spawn_retries_next_turn(self) -> None:
        layout = MazeLayout(width=3, height=1, walls=frozenset({normalize_edge((1, 0), (2, 0))}))
        rules = GreedyChaserRules()
        linked_spec = EnemySpec(
            enemy_type="linked_escape_hunter",
            role="linked_escape_hunter",
            movement_type="astar",
            move_priority="horizontal",
            step_count=1,
            lifetime_turns=3,
            traits=("escape_linked",),
        )
        blocked_spawner = ZoneSpawnerSpec(
            spawner_id="escape_zone_linked_hunter",
            enemy_spec=linked_spec,
            spawn_interval_turns=2,
            spawn_candidates=((1, 0),),
            source_zone_cells=((2, 0),),
            initial_delay_turns=1,
        )

        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(2, 0),
                enemy_positions=((1, 0),),
                enemy_states=(EnemyRuntimeState(),),
                spawner_states=(ZoneSpawnerState(turns_until_spawn=1),),
            ),
            action="skip",
            enemy_specs=(EnemySpec(move_priority="horizontal", step_count=1),),
            goal_cells=((0, 0),),
            zone_spawners=(blocked_spawner,),
        )

        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.spawned_enemies, ())
        self.assertEqual(next_state.spawner_states, (ZoneSpawnerState(turns_until_spawn=1),))

    def test_shared_turn_end_teleport_preserves_turn_end_trap_resolution_order(self) -> None:
        layout = MazeLayout(
            width=3,
            height=1,
            shared_teleport_pairs=(TeleportPair((1, 0), (2, 0)),),
        )
        rules = GreedyChaserRules()

        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(0, 0),
                enemy_positions=(),
            ),
            action="right",
            enemy_specs=(),
        )

        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.player_position, (2, 0))

    def test_zone_spawner_runtime_state_progresses_across_multiple_turns(self) -> None:
        layout = MazeLayout(width=5, height=2)
        rules = GreedyChaserRules()
        linked_spec = EnemySpec(
            enemy_type="linked_escape_hunter",
            role="linked_escape_hunter",
            movement_type="astar",
            move_priority="horizontal",
            step_count=1,
            lifetime_turns=3,
            traits=("escape_linked",),
        )
        spawner = ZoneSpawnerSpec(
            spawner_id="escape_zone_linked_hunter",
            enemy_spec=linked_spec,
            spawn_interval_turns=2,
            spawn_candidates=((4, 1),),
            source_zone_cells=((4, 0),),
            initial_delay_turns=2,
        )

        first_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(0, 1),
                enemy_positions=(),
                enemy_states=(),
                spawned_enemies=(),
                spawner_states=(ZoneSpawnerState(turns_until_spawn=2),),
            ),
            action="skip",
            enemy_specs=(),
            goal_cells=((4, 0),),
            zone_spawners=(spawner,),
        )

        self.assertIsNotNone(first_state)
        self.assertEqual(first_state.spawner_states, (ZoneSpawnerState(turns_until_spawn=1),))
        self.assertEqual(first_state.spawned_enemies, ())

        second_state = rules.step_state(
            layout,
            state=first_state,
            action="skip",
            enemy_specs=(),
            goal_cells=((4, 0),),
            zone_spawners=(spawner,),
        )

        self.assertIsNotNone(second_state)
        self.assertEqual(second_state.spawner_states, (ZoneSpawnerState(turns_until_spawn=2),))
        self.assertEqual(len(second_state.spawned_enemies), 1)
        self.assertEqual(second_state.spawned_enemies[0].source_spawner_id, "escape_zone_linked_hunter")

    def test_multiple_escape_zone_spawners_can_overlap_in_runtime_state(self) -> None:
        layout = MazeLayout(width=5, height=2)
        rules = GreedyChaserRules()
        linked_spec = EnemySpec(
            enemy_type="linked_escape_hunter",
            role="linked_escape_hunter",
            movement_type="astar",
            move_priority="horizontal",
            step_count=1,
            lifetime_turns=3,
            traits=("escape_linked",),
        )
        spawners = (
            ZoneSpawnerSpec(
                spawner_id="escape_zone_linked_hunter_a",
                enemy_spec=linked_spec,
                spawn_interval_turns=2,
                spawn_candidates=((0, 1),),
                source_zone_cells=((0, 0),),
                initial_delay_turns=1,
            ),
            ZoneSpawnerSpec(
                spawner_id="escape_zone_linked_hunter_b",
                enemy_spec=linked_spec,
                spawn_interval_turns=2,
                spawn_candidates=((4, 1),),
                source_zone_cells=((4, 0),),
                initial_delay_turns=1,
            ),
        )

        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(2, 0),
                enemy_positions=(),
                enemy_states=(),
                spawner_states=(
                    ZoneSpawnerState(turns_until_spawn=1),
                    ZoneSpawnerState(turns_until_spawn=1),
                ),
            ),
            action="skip",
            enemy_specs=(),
            goal_cells=((0, 0), (4, 0)),
            zone_spawners=spawners,
        )

        self.assertIsNotNone(next_state)
        self.assertEqual(
            sorted(enemy.position for enemy in next_state.spawned_enemies if enemy.position is not None),
            [(0, 0), (3, 1)],
        )
        self.assertEqual(
            tuple(enemy.source_spawner_id for enemy in next_state.spawned_enemies),
            ("escape_zone_linked_hunter_a", "escape_zone_linked_hunter_b"),
        )
        self.assertEqual(
            next_state.spawner_states,
            (
                ZoneSpawnerState(turns_until_spawn=2),
                ZoneSpawnerState(turns_until_spawn=2),
            ),
        )

    def test_newly_spawned_escape_hunter_acts_immediately_same_turn(self) -> None:
        layout = MazeLayout(width=3, height=2)
        rules = GreedyChaserRules()
        linked_spec = EnemySpec(
            enemy_type="linked_escape_hunter",
            role="linked_escape_hunter",
            movement_type="astar",
            move_priority="horizontal",
            step_count=2,
            lifetime_turns=3,
            traits=("escape_linked",),
        )
        spawner = ZoneSpawnerSpec(
            spawner_id="escape_zone_linked_hunter",
            enemy_spec=linked_spec,
            spawn_interval_turns=2,
            spawn_candidates=((2, 0),),
            source_zone_cells=((2, 0),),
            initial_delay_turns=1,
        )

        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(0, 0),
                enemy_positions=(),
                enemy_states=(),
                spawned_enemies=(),
                spawner_states=(ZoneSpawnerState(turns_until_spawn=1),),
            ),
            action="skip",
            enemy_specs=(),
            goal_cells=((2, 0),),
            zone_spawners=(spawner,),
        )

        self.assertIsNone(next_state)

    def test_spawner_runtime_state_round_trips_through_nonlethal_turn(self) -> None:
        layout = MazeLayout(width=4, height=2)
        rules = GreedyChaserRules()
        linked_spec = EnemySpec(
            enemy_type="linked_escape_hunter",
            role="linked_escape_hunter",
            movement_type="astar",
            move_priority="horizontal",
            step_count=1,
            lifetime_turns=3,
            traits=("escape_linked",),
        )
        spawner = ZoneSpawnerSpec(
            spawner_id="escape_zone_linked_hunter",
            enemy_spec=linked_spec,
            spawn_interval_turns=2,
            spawn_candidates=((3, 1),),
            source_zone_cells=((3, 0),),
            initial_delay_turns=1,
        )

        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(0, 1),
                enemy_positions=(),
                enemy_states=(),
                spawned_enemies=(),
                spawner_states=(ZoneSpawnerState(turns_until_spawn=1),),
            ),
            action="skip",
            enemy_specs=(),
            goal_cells=((3, 0),),
            zone_spawners=(spawner,),
        )

        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.player_position, (0, 1))
        self.assertEqual(next_state.spawner_states, (ZoneSpawnerState(turns_until_spawn=2),))
        self.assertEqual(len(next_state.spawned_enemies), 1)
        self.assertEqual(next_state.spawned_enemies[0].source_spawner_id, "escape_zone_linked_hunter")
        self.assertEqual(next_state.spawned_enemies[0].position, (2, 1))

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
                enemy_states=(EnemyRuntimeState(behavior_state=SamuraiBehaviorState(facing_index=0)),),
            ),
            action="skip",
            enemy_specs=(EnemySpec(enemy_type="samurai"),),
        )
        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.enemy_positions, ((0, 0),))
        self.assertEqual(
            next_state.enemy_states[0],
            EnemyRuntimeState(behavior_state=SamuraiBehaviorState(facing_index=1, attack_phase=0, turns_until_dash=3)),
        )

    def test_samurai_dashes_after_countdown_and_ignores_walls(self) -> None:
        layout = MazeLayout(width=6, height=6, walls=frozenset({normalize_edge((0, 0), (0, 1))}))
        rules = GreedyChaserRules()
        state = GameState(
            player_position=(2, 5),
            enemy_positions=((2, 0),),
            enemy_states=(EnemyRuntimeState(behavior_state=SamuraiBehaviorState(facing_index=2, attack_phase=0, turns_until_dash=1)),),
        )
        next_state = rules.step_state(
            layout,
            state=state,
            action="skip",
            enemy_specs=(EnemySpec(enemy_type="samurai"),),
        )
        self.assertIsNone(next_state)

    def test_patroller_advances_and_reverses_using_runtime_state(self) -> None:
        layout = MazeLayout(width=4, height=1)
        rules = GreedyChaserRules()
        spec = EnemySpec(
            enemy_type="patroller",
            role="patroller",
            movement_type="patrol",
            step_count=1,
            patrol_route=((0, 0), (1, 0), (2, 0)),
        )

        first_state = rules.step_state(
            layout,
            state=GameState(player_position=(3, 0), enemy_positions=((0, 0),)),
            action="skip",
            enemy_specs=(spec,),
        )
        self.assertIsNotNone(first_state)
        self.assertEqual(first_state.enemy_positions, ((1, 0),))
        self.assertEqual(
            first_state.enemy_states[0],
            EnemyRuntimeState(behavior_state=PatrollerBehaviorState(patrol_index=1, patrol_direction=1)),
        )

        second_state = rules.step_state(
            layout,
            state=first_state,
            action="skip",
            enemy_specs=(spec,),
        )
        self.assertIsNotNone(second_state)
        self.assertEqual(second_state.enemy_positions, ((2, 0),))
        self.assertEqual(
            second_state.enemy_states[0],
            EnemyRuntimeState(behavior_state=PatrollerBehaviorState(patrol_index=2, patrol_direction=1)),
        )

        third_state = rules.step_state(
            layout,
            state=second_state,
            action="skip",
            enemy_specs=(spec,),
        )
        self.assertIsNotNone(third_state)
        self.assertEqual(third_state.enemy_positions, ((1, 0),))
        self.assertEqual(
            third_state.enemy_states[0],
            EnemyRuntimeState(behavior_state=PatrollerBehaviorState(patrol_index=1, patrol_direction=-1)),
        )

    def test_patroller_reverses_when_forward_cell_is_blocked(self) -> None:
        layout = MazeLayout(width=3, height=2)
        rules = GreedyChaserRules()
        spec = EnemySpec(
            enemy_type="patroller",
            role="patroller",
            movement_type="patrol",
            step_count=1,
            patrol_route=((0, 0), (1, 0), (2, 0)),
        )

        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(0, 1),
                enemy_positions=((1, 0), (2, 0)),
                enemy_states=(
                    EnemyRuntimeState(behavior_state=PatrollerBehaviorState(patrol_index=1, patrol_direction=1)),
                    EnemyRuntimeState(),
                ),
            ),
            action="skip",
            enemy_specs=(
                spec,
                EnemySpec(
                    enemy_type="stationary_blocker",
                    role="stationary_blocker",
                    movement_type="stationary",
                    step_count=1,
                ),
            ),
        )
        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.enemy_positions, ((0, 0), (2, 0)))
        self.assertEqual(
            next_state.enemy_states[0],
            EnemyRuntimeState(behavior_state=PatrollerBehaviorState(patrol_index=0, patrol_direction=-1)),
        )

    def test_patroller_can_loop_across_full_route(self) -> None:
        layout = MazeLayout(width=2, height=2)
        rules = GreedyChaserRules()
        spec = EnemySpec(
            enemy_type="patroller",
            role="patroller",
            movement_type="patrol",
            step_count=1,
            patrol_route=((0, 0), (1, 0), (1, 1), (0, 1)),
            patrol_mode="loop",
        )

        state = GameState(player_position=(2, 2), enemy_positions=((0, 0),))
        positions: list[tuple[int, int] | None] = [state.enemy_positions[0]]
        for _ in range(4):
            next_state = rules.step_state(layout, state=state, action="skip", enemy_specs=(spec,))
            self.assertIsNotNone(next_state)
            state = next_state
            positions.append(state.enemy_positions[0])

        self.assertEqual(positions, [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])

    def test_patroller_loop_ignores_duplicated_terminal_start_cell(self) -> None:
        layout = MazeLayout(width=2, height=2)
        rules = GreedyChaserRules()
        spec = EnemySpec(
            enemy_type="patroller",
            role="patroller",
            movement_type="patrol",
            step_count=1,
            patrol_route=((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)),
            patrol_mode="loop",
        )

        state = GameState(player_position=(2, 2), enemy_positions=((0, 0),))
        positions: list[tuple[int, int] | None] = [state.enemy_positions[0]]
        for _ in range(4):
            next_state = rules.step_state(layout, state=state, action="skip", enemy_specs=(spec,))
            self.assertIsNotNone(next_state)
            state = next_state
            positions.append(state.enemy_positions[0])

        self.assertEqual(positions, [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])

    def test_stationary_blocker_keeps_player_goal_unsafely_occupied(self) -> None:
        layout = MazeLayout(width=3, height=1)
        rules = GreedyChaserRules()

        next_state = rules.step_state(
            layout,
            state=GameState(player_position=(0, 0), enemy_positions=((1, 0),)),
            action="right",
            enemy_specs=(
                EnemySpec(
                    enemy_type="stationary_blocker",
                    role="stationary_blocker",
                    movement_type="stationary",
                    step_count=1,
                ),
            ),
        )
        self.assertIsNone(next_state)

    def test_wanderer_uses_seeded_forward_left_right_preference(self) -> None:
        layout = MazeLayout(width=4, height=3)
        rules = GreedyChaserRules()
        spec = EnemySpec(
            enemy_type="wanderer",
            role="wanderer",
            movement_type="wander",
            step_count=1,
            facing_index=1,
            behavior_seed=8,
        )

        next_state = rules.step_state(
            layout,
            state=GameState(player_position=(3, 2), enemy_positions=((1, 1),)),
            action="skip",
            enemy_specs=(spec,),
        )
        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.enemy_positions, ((2, 1),))
        self.assertEqual(
            next_state.enemy_states[0],
            EnemyRuntimeState(behavior_state=WandererBehaviorState(facing_index=1, decision_count=1, visit_tick=1, visited_ticks=(((2, 1), 1),))),
        )

        repeated_state = rules.step_state(
            layout,
            state=GameState(player_position=(3, 2), enemy_positions=((1, 1),)),
            action="skip",
            enemy_specs=(spec,),
        )
        self.assertEqual(next_state, repeated_state)

    def test_wanderer_only_moves_back_when_forward_left_and_right_are_blocked(self) -> None:
        layout = MazeLayout(
            width=3,
            height=3,
            walls=frozenset(
                {
                    normalize_edge((1, 1), (2, 1)),
                    normalize_edge((1, 1), (1, 0)),
                    normalize_edge((1, 1), (1, 2)),
                }
            ),
        )
        rules = GreedyChaserRules()
        spec = EnemySpec(
            enemy_type="wanderer",
            role="wanderer",
            movement_type="wander",
            step_count=1,
            facing_index=1,
            behavior_seed=99,
        )

        next_state = rules.step_state(
            layout,
            state=GameState(player_position=(0, 2), enemy_positions=((1, 1),)),
            action="skip",
            enemy_specs=(spec,),
        )
        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.enemy_positions, ((0, 1),))
        self.assertEqual(
            next_state.enemy_states[0],
            EnemyRuntimeState(behavior_state=WandererBehaviorState(facing_index=3, decision_count=1, visit_tick=1, visited_ticks=(((0, 1), 1),))),
        )

    def test_wanderer_prefers_oldest_unvisited_forward_left_right_moves(self) -> None:
        layout = MazeLayout(width=3, height=3)
        rules = GreedyChaserRules()
        spec = EnemySpec(
            enemy_type="wanderer",
            role="wanderer",
            movement_type="wander",
            step_count=1,
            facing_index=1,
            behavior_seed=8,
        )

        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(2, 2),
                enemy_positions=((1, 1),),
                enemy_states=(
                    EnemyRuntimeState(
                        behavior_state=WandererBehaviorState(
                            facing_index=1,
                            decision_count=4,
                            visit_tick=4,
                            visited_ticks=(((2, 1), 3), ((1, 2), 4)),
                        )
                    ),
                ),
            ),
            action="skip",
            enemy_specs=(spec,),
        )
        self.assertIsNotNone(next_state)
        self.assertEqual(next_state.enemy_positions, ((1, 0),))
        self.assertEqual(
            next_state.enemy_states[0],
            EnemyRuntimeState(
                behavior_state=WandererBehaviorState(
                    facing_index=0,
                    decision_count=5,
                    visit_tick=5,
                    visited_ticks=(((1, 0), 5), ((1, 2), 4), ((2, 1), 3)),
                )
            ),
        )

    def test_wanderer_still_catches_player_after_long_recent_trail(self) -> None:
        layout = MazeLayout(width=3, height=3)
        rules = GreedyChaserRules()
        spec = EnemySpec(
            enemy_type="wanderer",
            role="wanderer",
            movement_type="wander",
            step_count=1,
            facing_index=1,
            behavior_seed=8,
        )

        next_state = rules.step_state(
            layout,
            state=GameState(
                player_position=(2, 1),
                enemy_positions=((1, 1),),
                enemy_states=(
                    EnemyRuntimeState(
                        behavior_state=WandererBehaviorState(
                            facing_index=1,
                            decision_count=20,
                            visit_tick=20,
                            visited_ticks=(((0, 1), 18), ((1, 0), 19), ((1, 2), 20), ((2, 1), 17)),
                        )
                    ),
                ),
            ),
            action="skip",
            enemy_specs=(spec,),
        )
        self.assertIsNone(next_state)

    def test_wanderer_explores_beyond_four_tile_loop_pattern(self) -> None:
        layout = MazeLayout(width=4, height=4)
        rules = GreedyChaserRules()
        spec = EnemySpec(
            enemy_type="wanderer",
            role="wanderer",
            movement_type="wander",
            step_count=1,
            facing_index=1,
            behavior_seed=8,
        )

        state = GameState(player_position=(3, 3), enemy_positions=((1, 1),))
        visited_positions = [state.enemy_positions[0]]
        for _ in range(8):
            next_state = rules.step_state(layout, state=state, action="skip", enemy_specs=(spec,))
            self.assertIsNotNone(next_state)
            state = next_state
            visited_positions.append(state.enemy_positions[0])

        self.assertGreaterEqual(len(set(visited_positions)), 6)


class MazeGeneratorTests(unittest.TestCase):
    def test_sample_positions_keeps_player_goal_and_enemies_distinct(self) -> None:
        generator = MazeGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
            enemy_specs=(EnemySpec(move_priority="horizontal"), EnemySpec(move_priority="vertical")),
        )
        player_start, enemy_spawns, goal, trap_cells, goal_cells, escape_zone_cells, zone_spawners = generator._sample_positions(MazeLayout(width=4, height=4))
        occupied = {player_start, goal}
        occupied.update(enemy.cell for enemy in enemy_spawns)
        occupied.update(trap_cells)

        self.assertEqual(len(enemy_spawns), 2)
        self.assertEqual(len(occupied), 4)
        self.assertEqual(goal_cells, (goal,))
        self.assertEqual(escape_zone_cells, ())
        self.assertEqual(zone_spawners, ())
        self.assertEqual(enemy_spawns[0].move_priority, "horizontal")
        self.assertEqual(enemy_spawns[1].move_priority, "vertical")

    def test_sample_positions_includes_distinct_traps_when_requested(self) -> None:
        generator = MazeGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
            trap_count=2,
        )
        player_start, enemy_spawns, goal, trap_cells, goal_cells, escape_zone_cells, zone_spawners = generator._sample_positions(MazeLayout(width=4, height=4))

        self.assertEqual(len(trap_cells), 2)
        self.assertEqual(len(set(trap_cells)), 2)
        self.assertNotIn(player_start, trap_cells)
        self.assertNotIn(goal, trap_cells)
        self.assertEqual(goal_cells, (goal,))
        self.assertEqual(escape_zone_cells, ())
        self.assertEqual(zone_spawners, ())
        self.assertTrue(all(enemy.cell not in trap_cells for enemy in enemy_spawns))

    def test_sample_positions_adds_escape_zone_spawner_beside_main_exit(self) -> None:
        generator = MazeGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
            enemy_specs=(),
            escape_zone_size=2,
        )

        player_start, enemy_spawns, goal, _trap_cells, goal_cells, escape_zone_cells, zone_spawners = generator._sample_positions(MazeLayout(width=6, height=6))

        self.assertEqual(enemy_spawns, ())
        self.assertEqual(goal_cells, (goal, *escape_zone_cells))
        self.assertEqual(len(escape_zone_cells), 4)
        self.assertNotIn(goal, escape_zone_cells)
        self.assertNotIn(player_start, escape_zone_cells)
        self.assertEqual(len(zone_spawners), 1)
        self.assertEqual(zone_spawners[0].source_zone_cells, escape_zone_cells)
        self.assertEqual(zone_spawners[0].enemy_spec.role, "linked_escape_hunter")
        self.assertEqual(zone_spawners[0].enemy_spec.movement_type, "astar")
        self.assertEqual(zone_spawners[0].enemy_spec.lifetime_turns, 3)
        self.assertEqual(zone_spawners[0].spawn_interval_turns, 2)

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
        self.assertEqual(specs[0].role, "x_chaser")
        self.assertEqual(specs[1].role, "y_chaser")
        self.assertEqual(specs[1].traits, ())
        self.assertEqual(specs[2].enemy_type, "samurai")
        self.assertEqual(specs[2].role, "dasher")
        self.assertEqual(
            config.generation_profile_id,
            "greedy_enemies_1x_1y_1samurai_1killer_2traps_2playerwalls_1enemywalls_0oneways_9x9_batch",
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

    def test_one_way_passages_are_added_disjoint_from_other_wall_layers(self) -> None:
        generator = MazeGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
            enemy_specs=(),
            player_only_wall_count=1,
            enemy_only_wall_count=1,
            one_way_passage_count=1,
        )
        layout = MazeLayout(
            width=3,
            height=2,
            walls=frozenset({normalize_edge((0, 0), (1, 0))}),
        )

        augmented_layout = generator._augment_layout_with_actor_walls(layout)

        self.assertIsNotNone(augmented_layout)
        self.assertEqual(len(augmented_layout.one_way_passages), 1)
        one_way_edge = next(iter(augmented_layout.one_way_passages))
        undirected_one_way_edge = normalize_edge(*one_way_edge)
        self.assertNotIn(undirected_one_way_edge, layout.walls)
        self.assertNotIn(undirected_one_way_edge, augmented_layout.player_only_walls)
        self.assertNotIn(undirected_one_way_edge, augmented_layout.enemy_only_walls)

    def test_try_record_rejects_safe_short_solution_before_full_solve(self) -> None:
        class FixedPositionGenerator(MazeGenerator):
            def _sample_positions(
                self,
                layout: MazeLayout,
            ) -> tuple[tuple[int, int], tuple[EnemySpawn, ...], tuple[int, int], tuple[tuple[int, int], ...], tuple[tuple[int, int], ...], tuple[tuple[int, int], ...], tuple]:
                return (
                    (0, 0),
                    (EnemySpawn.from_spec(EnemySpec(move_priority="horizontal"), (1, 1)),),
                    (0, 1),
                    (),
                    ((0, 1),),
                    (),
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

    def test_loop_patroller_generation_samples_adjacent_cycle(self) -> None:
        generator = MazeGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
            enemy_specs=(),
        )
        layout = MazeLayout(width=4, height=4)

        route = generator._sample_patrol_loop_route(layout, (1, 1))

        self.assertGreaterEqual(len(route), 4)
        self.assertEqual(route[0], (1, 1))
        self.assertEqual(len(route), len(set(route)))
        for index in range(len(route)):
            a = route[index]
            b = route[(index + 1) % len(route)]
            self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)

    def test_patroller_generation_prefers_longer_routes(self) -> None:
        generator = MazeGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
            enemy_specs=(),
        )
        layout = MazeLayout(width=6, height=6)

        route = generator._sample_patrol_route(layout, (2, 2))

        self.assertGreaterEqual(len(route), 8)
        self.assertEqual(route[0], (2, 2))
        self.assertEqual(len(route), len(set(route)))
        for index in range(len(route) - 1):
            a = route[index]
            b = route[index + 1]
            self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)

    def test_loop_patroller_generation_prefers_longer_cycles(self) -> None:
        generator = MazeGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
            enemy_specs=(),
        )
        layout = MazeLayout(width=6, height=6)

        route = generator._sample_patrol_loop_route(layout, (2, 2))

        self.assertGreaterEqual(len(route), 8)
        self.assertEqual(route[0], (2, 2))

    def test_loop_patroller_generation_downgrades_to_ping_pong_when_no_cycle_exists(self) -> None:
        generator = MazeGenerator(
            solver=MazeSolver(),
            rng=random.Random(4),
            enemy_specs=(),
        )
        layout = MazeLayout(width=4, height=1)
        spec = EnemySpec(
            enemy_type="patroller",
            role="patroller",
            movement_type="patrol",
            step_count=1,
            patrol_mode="loop",
        )

        spawn = generator._spawn_from_spec(layout, spec, (1, 0), 0)

        self.assertEqual(spawn.patrol_mode, "ping_pong")
        self.assertGreaterEqual(len(spawn.patrol_route), 2)
        for index in range(len(spawn.patrol_route) - 1):
            a = spawn.patrol_route[index]
            b = spawn.patrol_route[index + 1]
            self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)


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
            goal_cells=((1, 1), (2, 1), (3, 1), (2, 2), (3, 2)),
            escape_zone_cells=((2, 1), (3, 1), (2, 2), (3, 2)),
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
        self.assertIn("main_exit_cell = Vector2i(1, 1)", serialized)
        self.assertIn("exit_cells = Array[Vector2i]([Vector2i(1, 1), Vector2i(2, 1), Vector2i(3, 1), Vector2i(2, 2), Vector2i(3, 2)])", serialized)
        self.assertIn("main_exit_cells = Array[Vector2i]([Vector2i(1, 1)])", serialized)
        self.assertIn("win_zone_cells = Array[Vector2i]([Vector2i(1, 1), Vector2i(2, 1), Vector2i(3, 1), Vector2i(2, 2), Vector2i(3, 2)])", serialized)
        self.assertIn("escape_zone_cells = Array[Vector2i]([Vector2i(2, 1), Vector2i(3, 1), Vector2i(2, 2), Vector2i(3, 2)])", serialized)
        self.assertIn("escape_zone_spawners = Array[Dictionary]([])", serialized)
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
        self.assertIn('"canonical_archetype": "enemy.greedy_chaser.horizontal"', serialized)
        self.assertIn('"ecs_schema_version": 1', serialized)

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

    def test_serialize_writes_patrol_route_and_behavior_seed(self) -> None:
        exporter = GodotMazeExporter()
        record = MazeRecord(
            width=4,
            height=1,
            walls=(),
            teleport_pairs=(),
            enemy_teleport_pairs=(),
            shared_teleport_pairs=(),
            trap_cells=(),
            player_start=(0, 0),
            enemy_spawns=(
                EnemySpawn(
                    "wanderer",
                    (2, 0),
                    "horizontal",
                    role="wanderer",
                    movement_type="wander",
                    step_count=1,
                    facing_index=1,
                    behavior_seed=17,
                ),
                EnemySpawn(
                    "patroller",
                    (1, 0),
                    "horizontal",
                    role="patroller",
                    movement_type="patrol",
                    step_count=1,
                    patrol_route=((1, 0), (2, 0), (3, 0)),
                    patrol_mode="loop",
                ),
            ),
            goal=(3, 0),
            solution=("right", "right", "right"),
            iteration=1,
        )

        serialized = exporter.serialize(
            record=record,
            saved_at_unix=123,
            difficulty_label="probe",
            index=1,
            generation_profile_id="enemy_behavior_probe",
            cell_size=16,
        )

        self.assertIn('"behavior_seed": 17', serialized)
        self.assertIn('"patrol_route": Array[Vector2i]([Vector2i(1, 0), Vector2i(2, 0), Vector2i(3, 0)])', serialized)
        self.assertIn('"patrol_mode": "loop"', serialized)

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

    def test_serialize_writes_one_way_passages(self) -> None:
        exporter = GodotMazeExporter()
        record = MazeRecord(
            width=3,
            height=2,
            walls=(),
            player_only_walls=(),
            enemy_only_walls=(),
            one_way_passages=(((2, 0), (1, 0)),),
            teleport_pairs=(),
            enemy_teleport_pairs=(),
            shared_teleport_pairs=(),
            trap_cells=(),
            player_start=(0, 0),
            enemy_spawns=(),
            goal=(2, 0),
            solution=("down", "right", "right", "up"),
            iteration=1,
        )

        serialized = exporter.serialize(
            record=record,
            saved_at_unix=123,
            difficulty_label="probe",
            index=1,
            generation_profile_id="one_way_probe",
            cell_size=16,
        )

        self.assertIn('one_way_passages = Array[Dictionary]([{"from": Vector2i(2, 0), "to": Vector2i(1, 0)}])', serialized)


if __name__ == "__main__":
    unittest.main()
