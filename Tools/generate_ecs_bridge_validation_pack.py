from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from minotaur_export.exporter import GodotMazeExporter
from minotaur_export.generator import MazeGenerator
from minotaur_export.grid import MazeLayout, edge_sort_key
from minotaur_export.models import EnemySpec, ExportedMaze, MazeRecord
from minotaur_export.solver import MazeSolver


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "Resources" / "Worlds" / "SolverTestMazes" / "Probes" / "ECSBridge"
MANIFEST_PATH = OUTPUT_DIR / "ecs_bridge_validation_manifest.json"


@dataclass(frozen=True, slots=True)
class ProbeScenario:
    scenario_id: str
    display_name: str
    generation_profile_id: str
    width: int
    height: int
    min_moves: int
    seed: int
    enemy_specs: tuple[EnemySpec, ...]
    checks: tuple[str, ...]
    escape_zone_size: int = 1


SCENARIOS: tuple[ProbeScenario, ...] = (
    ProbeScenario(
        scenario_id="ecs_bridge_greedy_samurai",
        display_name="ECS Bridge Greedy Samurai",
        generation_profile_id="ecs_bridge_greedy_samurai",
        width=9,
        height=9,
        min_moves=18,
        seed=6101,
        enemy_specs=(
            EnemySpec(role="x_chaser", movement_type="greedy", move_priority="horizontal", step_count=2),
            EnemySpec(role="y_chaser", movement_type="greedy", move_priority="vertical", step_count=2),
            EnemySpec(enemy_type="samurai", role="dasher", movement_type="dash", step_count=1, facing_index=2),
        ),
        checks=(
            "Greedy chasers still respect component-driven axis priority.",
            "Samurai still rotates, charges, and dashes using component-facing state.",
            "Mixed legacy and canonical fields serialize together without runtime drift.",
        ),
    ),
    ProbeScenario(
        scenario_id="ecs_bridge_patroller_stationary_wanderer",
        display_name="ECS Bridge Patroller Stationary Wanderer",
        generation_profile_id="ecs_bridge_patroller_stationary_wanderer",
        width=8,
        height=8,
        min_moves=9,
        seed=6102,
        enemy_specs=(
            EnemySpec(enemy_type="patroller", role="patroller", movement_type="patrol", step_count=1),
            EnemySpec(enemy_type="stationary_blocker", role="stationary_blocker", movement_type="stationary", step_count=1),
            EnemySpec(enemy_type="wanderer", role="wanderer", movement_type="wander", step_count=1, facing_index=1),
        ),
        checks=(
            "Patroller reads patrol route and patrol mode from ecs_components.",
            "Stationary blocker remains immobile under component-driven movement family selection.",
            "Wanderer uses component-facing index and behavior seed without legacy-only reads.",
        ),
    ),
    ProbeScenario(
        scenario_id="ecs_bridge_escape_zone_linked_hunter",
        display_name="ECS Bridge Escape Zone Linked Hunter",
        generation_profile_id="ecs_bridge_escape_zone_linked_hunter",
        width=10,
        height=10,
        min_moves=20,
        seed=6103,
        enemy_specs=(
            EnemySpec(role="x_chaser", movement_type="greedy", move_priority="horizontal", step_count=2),
            EnemySpec(role="y_chaser", movement_type="greedy", move_priority="vertical", step_count=2),
        ),
        escape_zone_size=2,
        checks=(
            "Escape-zone spawner emits linked hunter payloads with canonical archetype fields.",
            "AStar linked hunter behavior still routes through the component-derived movement family.",
            "Spawn countdown, warning, and lifetime values remain aligned across Python and Godot.",
        ),
    ),
)


def generate_record(scenario: ProbeScenario) -> MazeRecord:
    solver = MazeSolver()
    rng = random.Random(scenario.seed)
    generator = MazeGenerator(
        solver=solver,
        rng=rng,
        enemy_specs=scenario.enemy_specs,
        trap_count=0,
        escape_zone_size=scenario.escape_zone_size,
    )
    all_edges = list(MazeLayout.build_all_edges(scenario.width, scenario.height))
    board_seed = scenario.seed
    attempts = 0

    while attempts < 400:
        walls_remaining = generator._build_connected_wall_set(scenario.width, scenario.height, all_edges)
        layout = MazeLayout(width=scenario.width, height=scenario.height, walls=frozenset(walls_remaining))
        normalized_walls = tuple(sorted(layout.walls, key=edge_sort_key))
        record = generator._try_record(
            layout=layout,
            normalized_walls=normalized_walls,
            min_moves=scenario.min_moves,
            iteration=1,
            board_seed=board_seed,
        )
        if record is not None:
            return record
        board_seed += 1
        attempts += 1

    raise RuntimeError(f"Unable to build probe record for {scenario.scenario_id} after {attempts} attempts")


def write_record(exporter: GodotMazeExporter, scenario: ProbeScenario, record: MazeRecord) -> ExportedMaze:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    serialized = exporter.serialize(
        record=record,
        saved_at_unix=scenario.seed,
        difficulty_label="probe",
        index=1,
        generation_profile_id=scenario.generation_profile_id,
        cell_size=16,
    )
    file_name = f"{scenario.scenario_id}_{record.width}x{record.height}_len{record.solution_total_steps:03d}_probe.tres"
    file_path = OUTPUT_DIR / file_name
    file_path.write_text(serialized, encoding="utf-8")
    return ExportedMaze(path=file_path, record=record, difficulty_label="probe")


def build_manifest(exported: list[tuple[ProbeScenario, ExportedMaze]]) -> dict:
    return {
        "id": "ecs_bridge_validation_pack",
        "generated_by": "Tools/generate_ecs_bridge_validation_pack.py",
        "probe_count": len(exported),
        "probes": [
            {
                "scenario_id": scenario.scenario_id,
                "display_name": scenario.display_name,
                "resource_path": str(exported_maze.path),
                "width": exported_maze.record.width,
                "height": exported_maze.record.height,
                "solution_total_steps": exported_maze.record.solution_total_steps,
                "generation_profile_id": scenario.generation_profile_id,
                "enemy_summary": [
                    {
                        "type": enemy.enemy_type,
                        "role": enemy.resolved_role,
                        "movement_type": enemy.resolved_movement_type,
                        "cell": list(enemy.cell),
                        "traits": list(enemy.traits),
                        "canonical_archetype": enemy.bridge_payload["archetype_id"],
                    }
                    for enemy in exported_maze.record.enemy_spawns
                ],
                "zone_spawners": [
                    {
                        "id": spawner.spawner_id,
                        "enemy_type": spawner.enemy_spec.enemy_type,
                        "role": spawner.enemy_spec.resolved_role,
                        "movement_type": spawner.enemy_spec.resolved_movement_type,
                        "canonical_archetype": spawner.enemy_spec.bridge_payload["archetype_id"],
                        "spawn_interval_turns": spawner.spawn_interval_turns,
                    }
                    for spawner in exported_maze.record.zone_spawners
                ],
                "checks": list(scenario.checks),
            }
            for scenario, exported_maze in exported
        ],
    }


def main() -> int:
    exporter = GodotMazeExporter()
    exported: list[tuple[ProbeScenario, ExportedMaze]] = []
    for scenario in SCENARIOS:
        record = generate_record(scenario)
        exported.append((scenario, write_record(exporter, scenario, record)))

    manifest = build_manifest(exported)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
