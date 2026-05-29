from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from minotaur_export.difficulty import DifficultyAssigner
from minotaur_export.exporter import GodotMazeExporter
from minotaur_export.generator import MazeGenerator
from minotaur_export.grid import MazeLayout
from minotaur_export.manifest import ManifestWriter
from minotaur_export.models import GenerationConfig, MazeRecord
from minotaur_export.solver import MazeSolver


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_EXPORT_DIR = ROOT_DIR / "Resources" / "Benchmarks"

SCENARIOS: dict[str, dict[str, Any]] = {
    "easy": {
        "width": 12,
        "height": 12,
        "mazes_per_iteration": 10,
        "min_moves": 30,
        "greedy_horizontal_count": 1,
        "greedy_vertical_count": 1,
        "killer_count": 0,
        "trap_count": 2,
    },
    "medium": {
        "width": 20,
        "height": 20,
        "mazes_per_iteration": 10,
        "min_moves": 40,
        "greedy_horizontal_count": 1,
        "greedy_vertical_count": 1,
        "killer_count": 0,
        "trap_count": 4,
    },
    "hard": {
        "width": 20,
        "height": 20,
        "mazes_per_iteration": 10,
        "min_moves": 60,
        "greedy_horizontal_count": 2,
        "greedy_vertical_count": 2,
        "killer_count": 1,
        "trap_count": 4,
    },
}


def build_config(scenario_name: str, seed: int, maze_count: int | None = None) -> GenerationConfig:
    scenario = SCENARIOS[scenario_name]
    scenario = dict(scenario)
    if maze_count is not None:
        scenario["mazes_per_iteration"] = maze_count
    return GenerationConfig(
        source_project=ROOT_DIR,
        output_dir=ROOT_DIR / "Tools" / ".tmp_benchmark_output",
        iterations=1,
        seed=seed,
        additional_checks=True,
        additional_check_threshold=50,
        **scenario,
    )


def validate_record(record: MazeRecord, config: GenerationConfig, solver: MazeSolver) -> list[str]:
    issues: list[str] = []
    enemy_specs = config.enemy_specs
    enemy_starts = tuple(enemy.cell for enemy in record.enemy_spawns)

    if len(record.enemy_spawns) != len(enemy_specs):
        issues.append(f"enemy_count={len(record.enemy_spawns)} expected={len(enemy_specs)}")
    if len(record.trap_cells) != config.trap_count:
        issues.append(f"trap_count={len(record.trap_cells)} expected={config.trap_count}")
    if record.solution_total_steps < config.min_moves:
        issues.append(f"solution_total_steps={record.solution_total_steps} below min_moves={config.min_moves}")

    if not solver.sequence_is_safe(
        layout=record_layout(record),
        player_start=record.player_start,
        enemy_starts=enemy_starts,
        actions=record.solution,
        goal=record.goal,
        enemy_specs=enemy_specs,
        trap_cells=record.trap_cells,
    ):
        issues.append("recorded solution is not safe/valid")

    return issues


def record_layout(record: MazeRecord) -> MazeLayout:
    return MazeLayout(width=record.width, height=record.height, walls=frozenset(record.walls))

def run_benchmark(scenario_name: str, seed: int, maze_count: int | None = None) -> dict[str, Any]:
    config = build_config(scenario_name, seed, maze_count=maze_count)
    solver = MazeSolver(rules=GreedyChaserRules())
    generator = MazeGenerator(
        solver=solver,
        rng=random.Random(config.seed),
        enemy_specs=config.enemy_specs,
        trap_count=config.trap_count,
    )

    started = time.perf_counter()
    records = generator.generate_batch(
        width=config.width,
        height=config.height,
        min_moves=config.min_moves,
        target_count=config.mazes_per_iteration,
        iteration=1,
        additional_checks=config.additional_checks,
        additional_check_threshold=config.additional_check_threshold,
    )
    duration_seconds = time.perf_counter() - started

    validation_errors: list[str] = []
    for index, record in enumerate(records, start=1):
        for issue in validate_record(record, config, solver):
            validation_errors.append(f"record {index}: {issue}")

    solution_lengths = [record.solution_total_steps for record in records]
    return {
        "scenario": scenario_name,
        "seed": seed,
        "duration_seconds": round(duration_seconds, 6),
        "maze_count": len(records),
        "mazes_per_minute": round((len(records) / duration_seconds) * 60, 3) if duration_seconds > 0 else None,
        "average_solution_length": round(mean(solution_lengths), 3) if solution_lengths else None,
        "max_solution_length": max(solution_lengths) if solution_lengths else None,
        "min_solution_length": min(solution_lengths) if solution_lengths else None,
        "validation_passed": not validation_errors,
        "validation_errors": validation_errors,
        "config": {
            "width": config.width,
            "height": config.height,
            "mazes_per_iteration": config.mazes_per_iteration,
            "min_moves": config.min_moves,
            "greedy_horizontal_count": config.greedy_horizontal_count,
            "greedy_vertical_count": config.greedy_vertical_count,
            "killer_count": config.killer_count,
            "trap_count": config.trap_count,
            "additional_checks": config.additional_checks,
            "additional_check_threshold": config.additional_check_threshold,
        },
    }


def export_records(
    scenario_name: str,
    config: GenerationConfig,
    records: list[MazeRecord],
    export_dir: Path,
) -> dict[str, Any]:
    export_dir.mkdir(parents=True, exist_ok=True)
    exporter = GodotMazeExporter()
    manifest_writer = ManifestWriter()
    difficulty_labels = DifficultyAssigner().assign(records)
    saved_at_unix = int(time.time())
    exported = []

    for index, record in enumerate(records, start=1):
        exported.append(
            exporter.write_record(
                record=record,
                output_dir=export_dir,
                saved_at_unix=saved_at_unix + index - 1,
                difficulty_label=difficulty_labels[record],
                index=index,
                generation_profile_id=f"benchmark_{scenario_name}_seed_{config.seed}",
                cell_size=config.cell_size,
            )
        )

    manifest_path = export_dir / f"benchmark_manifest_{scenario_name}_{config.seed}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    manifest_writer.write(manifest_path=manifest_path, config=config, generated_records=exported)
    return {
        "export_dir": str(export_dir),
        "manifest_path": str(manifest_path),
        "exported_files": [str(item.path) for item in exported],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Minotaur maze generation for a single scenario and seed.")
    parser.add_argument("--scenario", choices=tuple(SCENARIOS.keys()), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--maze-count", type=int, default=None)
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    args = parser.parse_args()

    result = run_benchmark(args.scenario, args.seed, maze_count=args.maze_count)
    if args.export:
        config = build_config(args.scenario, args.seed, maze_count=args.maze_count)
        solver = MazeSolver(rules=GreedyChaserRules())
        generator = MazeGenerator(
            solver=solver,
            rng=random.Random(config.seed),
            enemy_specs=config.enemy_specs,
            trap_count=config.trap_count,
        )
        records = generator.generate_batch(
            width=config.width,
            height=config.height,
            min_moves=config.min_moves,
            target_count=config.mazes_per_iteration,
            iteration=1,
            additional_checks=config.additional_checks,
            additional_check_threshold=config.additional_check_threshold,
        )
        result["export"] = export_records(args.scenario, config, records, args.export_dir)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
