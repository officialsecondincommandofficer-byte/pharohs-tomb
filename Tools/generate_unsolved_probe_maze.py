from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from minotaur_export.exporter import GodotMazeExporter
from minotaur_export.generator import MazeGenerator
from minotaur_export.grid import MazeLayout, edge_sort_key
from minotaur_export.models import EnemySpec, MazeRecord
from minotaur_export.solver import MazeSolver


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "Resources" / "Worlds" / "SolverTestMazes" / "Probes"


def build_enemy_specs(
    greedy_horizontal_count: int,
    greedy_vertical_count: int,
    samurai_count: int,
    killer_count: int,
) -> tuple[EnemySpec, ...]:
    specs: list[EnemySpec] = []
    specs.extend(EnemySpec(move_priority="horizontal") for _ in range(greedy_horizontal_count))
    specs.extend(EnemySpec(move_priority="vertical") for _ in range(greedy_vertical_count))
    specs.extend(EnemySpec(enemy_type="samurai", step_count=1, facing_index=2) for _ in range(samurai_count))
    return tuple(
        EnemySpec(
            enemy_type=spec.enemy_type,
            move_priority=spec.move_priority,
            step_count=spec.step_count,
            facing_index=spec.facing_index,
            traits=("killer",) if index < killer_count else (),
        )
        for index, spec in enumerate(specs)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one connected probe maze without proving solvability.")
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--height", type=int, default=8)
    parser.add_argument("--seed", type=int, default=2000)
    parser.add_argument("--greedy-horizontal-count", type=int, default=0)
    parser.add_argument("--greedy-vertical-count", type=int, default=0)
    parser.add_argument("--samurai-count", type=int, default=2)
    parser.add_argument("--killer-count", type=int, default=0)
    parser.add_argument("--trap-count", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    enemy_specs = build_enemy_specs(
        greedy_horizontal_count=args.greedy_horizontal_count,
        greedy_vertical_count=args.greedy_vertical_count,
        samurai_count=args.samurai_count,
        killer_count=args.killer_count,
    )
    generator = MazeGenerator(
        solver=MazeSolver(),
        rng=rng,
        enemy_specs=enemy_specs,
        trap_count=args.trap_count,
    )

    all_edges = list(MazeLayout.build_all_edges(args.width, args.height))
    walls_remaining = generator._build_connected_wall_set(args.width, args.height, all_edges)
    layout = MazeLayout(width=args.width, height=args.height, walls=frozenset(walls_remaining))
    normalized_walls = tuple(sorted(layout.walls, key=edge_sort_key))
    player_start, enemy_spawns, goal, trap_cells = generator._sample_positions(layout)

    record = MazeRecord(
        width=args.width,
        height=args.height,
        walls=normalized_walls,
        trap_cells=trap_cells,
        player_start=player_start,
        enemy_spawns=enemy_spawns,
        goal=goal,
        solution=(),
        iteration=1,
        seed_hint=args.seed,
    )

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    exporter = GodotMazeExporter()
    saved_at_unix = int(time.time())
    exported = exporter.write_record(
        record=record,
        output_dir=output_dir,
        saved_at_unix=saved_at_unix,
        difficulty_label="probe",
        index=1,
        generation_profile_id="unverified_probe",
        cell_size=16,
    )

    print(
        json.dumps(
            {
                "resource_path": str(exported.path),
                "seed": args.seed,
                "width": args.width,
                "height": args.height,
                "player_start": list(player_start),
                "goal": list(goal),
                "trap_cells": [list(cell) for cell in trap_cells],
                "enemy_spawns": [
                    {
                        "type": enemy.enemy_type,
                        "cell": list(enemy.cell),
                        "move_priority": enemy.move_priority,
                        "step_count": enemy.step_count,
                        "facing_index": enemy.facing_index,
                        "traits": list(enemy.traits),
                    }
                    for enemy in enemy_spawns
                ],
                "wall_count": len(normalized_walls),
                "solvability_verified": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
