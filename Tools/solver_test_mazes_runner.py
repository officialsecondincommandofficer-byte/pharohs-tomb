from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmark_minotaur_generation import validate_record
from minotaur_export.difficulty import DifficultyAssigner
from minotaur_export.exporter import GodotMazeExporter
from minotaur_export.generator import MazeGenerator
from minotaur_export.manifest import ManifestWriter
from minotaur_export.models import GenerationConfig, MazeRecord
from minotaur_export.rules import GreedyChaserRules
from minotaur_export.service import ExportService
from minotaur_export.solver import MazeSolver


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX_PATH = ROOT_DIR / "Tools" / "solver_test_mazes_regression_matrix.json"
DEFAULT_WORLD_DIR = ROOT_DIR / "Resources" / "Worlds" / "SolverTestMazes"


@dataclass(frozen=True, slots=True)
class MazeSpec:
    id: str
    display_name: str
    category: str
    tier: str
    width: int
    height: int
    min_moves: int
    greedy_horizontal_count: int
    greedy_vertical_count: int
    samurai_count: int
    killer_count: int
    trap_count: int
    intent: str


def load_matrix(matrix_path: Path) -> dict[str, Any]:
    return json.loads(matrix_path.read_text(encoding="utf-8"))


def load_specs(matrix_path: Path) -> tuple[list[MazeSpec], dict[str, list[str]]]:
    matrix = load_matrix(matrix_path)
    specs = [MazeSpec(**raw_spec) for raw_spec in matrix["maze_specs"]]
    benchmark_matrix = {
        str(key): [str(item) for item in value]
        for key, value in matrix.get("benchmark_matrix", {}).items()
    }
    return specs, benchmark_matrix


def filter_specs(
    specs: list[MazeSpec],
    benchmark_matrix: dict[str, list[str]],
    selected_ids: list[str] | None,
    tier: str | None,
    limit: int | None,
) -> list[MazeSpec]:
    selected: list[MazeSpec]
    if selected_ids:
        wanted = set(selected_ids)
        selected = [spec for spec in specs if spec.id in wanted]
    elif tier:
        tier_ids = benchmark_matrix.get(tier, [])
        wanted = set(tier_ids)
        selected = [spec for spec in specs if spec.id in wanted]
    else:
        selected = list(specs)

    if limit is not None:
        selected = selected[:limit]
    return selected


def build_generation_config(
    spec: MazeSpec,
    seed: int,
    output_dir: Path,
    additional_checks: bool,
) -> GenerationConfig:
    return GenerationConfig(
        source_project=ROOT_DIR,
        output_dir=output_dir,
        width=spec.width,
        height=spec.height,
        iterations=1,
        mazes_per_iteration=1,
        min_moves=spec.min_moves,
        seed=seed,
        greedy_horizontal_count=spec.greedy_horizontal_count,
        greedy_vertical_count=spec.greedy_vertical_count,
        samurai_count=spec.samurai_count,
        killer_count=spec.killer_count,
        trap_count=spec.trap_count,
        additional_checks=additional_checks,
        additional_check_threshold=max(50, spec.min_moves),
    )


def build_generator(config: GenerationConfig) -> MazeGenerator:
    return MazeGenerator(
        solver=MazeSolver(rules=GreedyChaserRules()),
        rng=random.Random(config.seed),
        enemy_specs=config.enemy_specs,
        trap_count=config.trap_count,
    )


def _make_progress_callback(spec: MazeSpec):
    def _callback(payload: dict) -> None:
        event = payload["event"]
        if event == "board_seed_started":
            print(
                "[debug] %s board_seed=%s walls=%s generated=%s attempts=%s rejections=%s longest=%s"
                % (
                    spec.id,
                    payload["board_seed"],
                    payload["walls_remaining"],
                    payload["generated_count"],
                    payload["attempts"],
                    payload["rejections"],
                    payload["largest_solution"],
                )
            )
        elif event == "layout_started":
            print(
                "[debug] %s layout=%s board_seed=%s walls=%s checks=%s"
                % (
                    spec.id,
                    payload["layout_index"],
                    payload["board_seed"],
                    payload["walls_remaining"],
                    payload["checks_remaining"],
                )
            )
        elif event == "progress":
            print(
                "[debug] %s progress layout=%s attempts=%s rejections=%s checks_left=%s longest=%s"
                % (
                    spec.id,
                    payload["layout_index"],
                    payload["attempts"],
                    payload["rejections"],
                    payload["checks_remaining"],
                    payload["largest_solution"],
                )
            )
        elif event == "record_found":
            print(
                "[debug] %s record_found steps=%s layout=%s attempts=%s rejections=%s start=%s goal=%s traps=%s"
                % (
                    spec.id,
                    payload["solution_total_steps"],
                    payload["layout_index"],
                    payload["attempts"],
                    payload["rejections"],
                    payload["player_start"],
                    payload["goal"],
                    payload["trap_count"],
                )
            )
        elif event == "additional_checks_expanded":
            print(
                "[debug] %s additional_checks longest=%s checks_left=%s layout=%s"
                % (
                    spec.id,
                    payload["largest_solution"],
                    payload["checks_remaining"],
                    payload["layout_index"],
                )
            )

    return _callback


def benchmark_spec(spec: MazeSpec, seed: int, additional_checks: bool, debug_progress: bool) -> dict[str, Any]:
    config = build_generation_config(
        spec,
        seed=seed,
        output_dir=ROOT_DIR / "Tools" / ".tmp_solver_test_mazes",
        additional_checks=additional_checks,
    )
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
        target_count=1,
        iteration=1,
        additional_checks=config.additional_checks,
        additional_check_threshold=config.additional_check_threshold,
        progress_callback=_make_progress_callback(spec) if debug_progress else None,
    )
    duration_seconds = time.perf_counter() - started

    record: MazeRecord | None = records[0] if records else None
    issues = validate_record(record, config, solver) if record is not None else ["no maze generated"]

    return {
        "id": spec.id,
        "display_name": spec.display_name,
        "tier": spec.tier,
        "category": spec.category,
        "seed": seed,
        "width": spec.width,
        "height": spec.height,
        "min_moves": spec.min_moves,
        "duration_seconds": round(duration_seconds, 6),
        "validation_passed": not issues,
        "validation_errors": issues,
        "solution_total_steps": record.solution_total_steps if record is not None else None,
        "enemy_counts": {
            "greedy_horizontal": spec.greedy_horizontal_count,
            "greedy_vertical": spec.greedy_vertical_count,
            "samurai": spec.samurai_count,
            "killer": spec.killer_count,
        },
        "trap_count": spec.trap_count,
        "intent": spec.intent,
    }


def export_spec(spec: MazeSpec, seed: int, output_dir: Path, additional_checks: bool) -> dict[str, Any]:
    config = build_generation_config(
        spec,
        seed=seed,
        output_dir=output_dir,
        additional_checks=additional_checks,
    )
    service = ExportService(
        generator=build_generator(config),
        difficulty_assigner=DifficultyAssigner(),
        exporter=GodotMazeExporter(),
        manifest_writer=ManifestWriter(),
        logger=lambda _message: None,
    )
    started = time.perf_counter()
    summary = service.run(config)
    duration_seconds = time.perf_counter() - started
    exported = summary.exported_mazes[0] if summary.exported_mazes else None
    return {
        "id": spec.id,
        "display_name": spec.display_name,
        "seed": seed,
        "duration_seconds": round(duration_seconds, 6),
        "manifest_path": str(summary.manifest_path),
        "resource_path": str(exported.path) if exported is not None else None,
        "solution_total_steps": exported.record.solution_total_steps if exported is not None else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark or export the SolverTestMazes regression suite.")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX_PATH)
    parser.add_argument("--tier", choices=("smoke", "behavior", "stress", "extreme"), default=None)
    parser.add_argument("--ids", nargs="+", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed-base", type=int, default=1000)
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_WORLD_DIR)
    parser.add_argument("--additional-checks", action="store_true")
    parser.add_argument("--debug-progress", action="store_true")
    args = parser.parse_args()

    specs, benchmark_matrix = load_specs(args.matrix)
    selected_specs = filter_specs(specs, benchmark_matrix, selected_ids=args.ids, tier=args.tier, limit=args.limit)
    if not selected_specs:
        raise SystemExit("No maze specs selected.")

    results: list[dict[str, Any]] = []
    for index, spec in enumerate(selected_specs, start=1):
        seed = args.seed_base + index - 1
        if args.export:
            results.append(
                export_spec(
                    spec,
                    seed=seed,
                    output_dir=args.output_dir,
                    additional_checks=args.additional_checks,
                )
            )
        else:
            results.append(
                benchmark_spec(
                    spec,
                    seed=seed,
                    additional_checks=args.additional_checks,
                    debug_progress=args.debug_progress,
                )
            )

    print(
        json.dumps(
            {
                "matrix": str(args.matrix),
                "mode": "export" if args.export else "benchmark",
                "selected_ids": [spec.id for spec in selected_specs],
                "seed_base": args.seed_base,
                "additional_checks": args.additional_checks,
                "debug_progress": args.debug_progress,
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
