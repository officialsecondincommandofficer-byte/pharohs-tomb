from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Sequence

from .difficulty import DifficultyAssigner
from .exporter import GodotMazeExporter
from .generator import MazeGenerator
from .manifest import ManifestWriter
from .models import GenerationConfig
from .rules import GreedyChaserRules
from .service import ExportService
from .solver import MazeSolver


DEFAULT_SOURCE_PROJECT = Path(r"C:\Users\echri\Python Projects\Minotaur-Project")
DEFAULT_OUTPUT_DIR = Path(
    r"C:\Users\echri\godotFolder\Godot_v4.5.1-stable_mono_win64\godot_v4.5.1_projects\Pharohs_Tomb\pharohs-tomb\Resources"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a batch of solvable Minotaur mazes and export them as "
            "Godot SavedMazeResource .tres files."
        )
    )
    parser.add_argument("--source-project", type=Path, default=DEFAULT_SOURCE_PROJECT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=9)
    parser.add_argument("--height", type=int, default=9)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--mazes-per-iteration", type=int, default=10)
    parser.add_argument("--min-moves", type=int, default=30)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--cell-size", type=int, default=16)
    parser.add_argument("--enemy-move-priority", choices=("horizontal", "vertical"), default="horizontal")
    parser.add_argument("--greedy-horizontal-count", type=int, default=None)
    parser.add_argument("--greedy-vertical-count", type=int, default=None)
    parser.add_argument("--samurai-count", type=int, default=0)
    parser.add_argument("--killer-count", type=int, default=0)
    parser.add_argument("--trap-count", type=int, default=0)
    parser.add_argument("--additional-check-threshold", type=int, default=50)
    parser.add_argument("--additional-checks", dest="additional_checks", action="store_true")
    parser.add_argument("--no-additional-checks", dest="additional_checks", action="store_false")
    parser.set_defaults(additional_checks=True)
    return parser


def parse_args(argv: Sequence[str] | None = None) -> GenerationConfig:
    args = build_parser().parse_args(argv)
    any_count_arg = args.greedy_horizontal_count is not None or args.greedy_vertical_count is not None
    greedy_horizontal_count = 1 if args.greedy_horizontal_count is None else args.greedy_horizontal_count
    greedy_vertical_count = 0 if args.greedy_vertical_count is None else args.greedy_vertical_count
    if not any_count_arg and args.enemy_move_priority == "vertical":
        greedy_horizontal_count = 0
        greedy_vertical_count = 1
    if greedy_horizontal_count < 0 or greedy_vertical_count < 0 or args.samurai_count < 0:
        build_parser().error("enemy counts must be zero or greater")
    total_enemy_count = greedy_horizontal_count + greedy_vertical_count + args.samurai_count
    if total_enemy_count <= 0:
        build_parser().error("at least one enemy is required")
    if total_enemy_count > args.width * args.height - 2:
        build_parser().error("enemy counts leave no room for distinct player and exit cells")
    if args.killer_count < 0:
        build_parser().error("killer count must be zero or greater")
    if args.killer_count > total_enemy_count:
        build_parser().error("killer count cannot exceed total enemy count")
    if args.trap_count < 0:
        build_parser().error("trap count must be zero or greater")
    if args.trap_count > args.width * args.height - total_enemy_count - 2:
        build_parser().error("trap count leaves no room for distinct player, exit, and enemy cells")

    return GenerationConfig(
        source_project=args.source_project,
        output_dir=args.output_dir,
        width=args.width,
        height=args.height,
        iterations=args.iterations,
        mazes_per_iteration=args.mazes_per_iteration,
        min_moves=args.min_moves,
        seed=args.seed,
        cell_size=args.cell_size,
        enemy_move_priority=args.enemy_move_priority,
        greedy_horizontal_count=greedy_horizontal_count,
        greedy_vertical_count=greedy_vertical_count,
        samurai_count=args.samurai_count,
        killer_count=args.killer_count,
        trap_count=args.trap_count,
        additional_check_threshold=args.additional_check_threshold,
        additional_checks=args.additional_checks,
    )


def build_service(config: GenerationConfig | None = None) -> ExportService:
    config = config or GenerationConfig(source_project=DEFAULT_SOURCE_PROJECT, output_dir=DEFAULT_OUTPUT_DIR)
    solver = MazeSolver(rules=GreedyChaserRules())
    generator = MazeGenerator(solver=solver, rng=random.Random(), enemy_specs=config.enemy_specs, trap_count=config.trap_count)
    return ExportService(
        generator=generator,
        difficulty_assigner=DifficultyAssigner(),
        exporter=GodotMazeExporter(),
        manifest_writer=ManifestWriter(),
    )


def main(argv: Sequence[str] | None = None) -> int:
    config = parse_args(argv)
    service = build_service(config)
    service.generator.rng.seed(config.seed)
    service.run(config)
    return 0
