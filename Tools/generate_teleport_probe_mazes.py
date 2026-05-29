from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from minotaur_export.exporter import GodotMazeExporter
from minotaur_export.generator import MazeGenerator
from minotaur_export.grid import MazeLayout, edge_sort_key
from minotaur_export.models import EnemySpec, EnemySpawn, MazeRecord, TeleportPair
from minotaur_export.solver import MazeSolver


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "Resources" / "Worlds" / "SolverTestMazes" / "Probes"


def build_enemy_specs() -> tuple[EnemySpec, ...]:
    return (
        EnemySpec(move_priority="horizontal"),
        EnemySpec(move_priority="vertical"),
    )


def build_enemy_specs_from_counts(greedy_horizontal_count: int, greedy_vertical_count: int) -> tuple[EnemySpec, ...]:
    specs: list[EnemySpec] = []
    specs.extend(EnemySpec(move_priority="horizontal") for _ in range(greedy_horizontal_count))
    specs.extend(EnemySpec(move_priority="vertical") for _ in range(greedy_vertical_count))
    return tuple(specs)


def sample_teleport_pairs(
    layout: MazeLayout,
    rng: random.Random,
    pair_count: int,
    reserved: set[tuple[int, int]],
) -> tuple[TeleportPair, ...]:
    occupied = set(reserved)
    pairs: list[TeleportPair] = []
    for _ in range(pair_count):
        a = sample_distinct_cell(layout, rng, occupied)
        occupied.add(a)
        b = sample_distinct_cell(layout, rng, occupied)
        occupied.add(b)
        pairs.append(TeleportPair(a, b).normalized())
    return tuple(sorted(pairs, key=lambda pair: (pair.a[1], pair.a[0], pair.b[1], pair.b[0])))


def sample_distinct_cell(layout: MazeLayout, rng: random.Random, occupied: set[tuple[int, int]]) -> tuple[int, int]:
    while True:
        cell = layout.random_cell(rng)
        if cell not in occupied:
            return cell


def solution_uses_teleport(layout: MazeLayout, start: tuple[int, int], actions: tuple[str, ...]) -> bool:
    rules = MazeSolver().rules
    current = start
    for action in actions:
        transition = rules.resolve_player_transition(layout, current, action)
        if transition.used_teleport:
            return True
        current = transition.resolved_cell
    return False


def build_record(
    layout: MazeLayout,
    normalized_walls: tuple[tuple[tuple[int, int], tuple[int, int]], ...],
    player_start: tuple[int, int],
    enemy_spawns: tuple[EnemySpawn, ...],
    goal: tuple[int, int],
    solution: tuple[str, ...],
    seed_hint: int,
) -> MazeRecord:
    return MazeRecord(
        width=layout.width,
        height=layout.height,
        walls=normalized_walls,
        trap_cells=(),
        player_start=player_start,
        enemy_spawns=enemy_spawns,
        goal=goal,
        solution=solution,
        iteration=1,
        teleport_pairs=layout.teleport_pairs,
        seed_hint=seed_hint,
    )


def try_find_record(
    rng: random.Random,
    solver: MazeSolver,
    width: int,
    height: int,
    min_moves: int,
    teleport_pair_count: int,
    wall_attempts: int,
    position_attempts: int,
    board_seed: int,
    enemy_specs: tuple[EnemySpec, ...],
    require_teleport_usage: bool,
) -> MazeRecord | None:
    generator = MazeGenerator(solver=solver, rng=rng, enemy_specs=enemy_specs, trap_count=0)
    all_edges = list(MazeLayout.build_all_edges(width, height))
    walls_remaining = generator._build_connected_wall_set(width, height, all_edges)
    normalized_walls = tuple(sorted(walls_remaining, key=edge_sort_key))
    base_layout = MazeLayout(width=width, height=height, walls=frozenset(walls_remaining))

    for _ in range(wall_attempts):
        teleport_pairs = sample_teleport_pairs(base_layout, rng, teleport_pair_count, reserved=set())
        layout = MazeLayout(width=width, height=height, walls=frozenset(walls_remaining), teleport_pairs=teleport_pairs)

        for _ in range(position_attempts):
            player_start = layout.random_cell(rng)
            goal = layout.random_cell(rng)
            if player_start == goal:
                continue

            occupied = {player_start, goal}
            enemy_spawns: list[EnemySpawn] = []
            for spec in enemy_specs:
                enemy_cell = sample_distinct_cell(layout, rng, occupied)
                occupied.add(enemy_cell)
                enemy_spawns.append(EnemySpawn.from_spec(spec, enemy_cell))

            result = solver.solve(
                layout,
                player_start=player_start,
                enemy_starts=tuple(enemy.cell for enemy in enemy_spawns),
                goal=goal,
                enemy_specs=enemy_specs,
                trap_cells=(),
            )
            if not result.solvable or result.total_steps < min_moves:
                continue
            if require_teleport_usage and not solution_uses_teleport(layout, player_start, result.actions):
                continue

            return build_record(
                layout=layout,
                normalized_walls=normalized_walls,
                player_start=player_start,
                enemy_spawns=tuple(enemy_spawns),
                goal=goal,
                solution=result.actions,
                seed_hint=board_seed,
            )

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate solvable teleport probe mazes for SolverTestMazes.")
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--height", type=int, default=8)
    parser.add_argument("--min-moves", type=int, default=30)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--seed", type=int, default=4200)
    parser.add_argument("--teleport-pair-count", type=int, default=2)
    parser.add_argument("--greedy-horizontal-count", type=int, default=1)
    parser.add_argument("--greedy-vertical-count", type=int, default=1)
    parser.add_argument("--no-require-teleport-usage", action="store_true")
    parser.add_argument("--wall-attempts", type=int, default=30)
    parser.add_argument("--position-attempts", type=int, default=500)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    solver = MazeSolver()
    exporter = GodotMazeExporter()
    enemy_specs = build_enemy_specs_from_counts(args.greedy_horizontal_count, args.greedy_vertical_count)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    seen_signatures: set[tuple] = set()
    board_seed = args.seed
    started = time.perf_counter()

    while len(records) < args.count:
        record = try_find_record(
            rng=rng,
            solver=solver,
            width=args.width,
            height=args.height,
            min_moves=args.min_moves,
            teleport_pair_count=args.teleport_pair_count,
            wall_attempts=args.wall_attempts,
            position_attempts=args.position_attempts,
            board_seed=board_seed,
            enemy_specs=enemy_specs,
            require_teleport_usage=not args.no_require_teleport_usage,
        )
        board_seed += 1
        if record is None:
            continue
        if record.signature() in seen_signatures:
            continue
        seen_signatures.add(record.signature())

        exported = exporter.write_record(
            record=record,
            output_dir=output_dir,
            saved_at_unix=int(time.time()),
            difficulty_label="probe",
            index=len(records) + 1,
            generation_profile_id="teleport_probe_batch",
            cell_size=16,
        )
        records.append(
            {
                "resource_path": str(exported.path),
                "solution_total_steps": record.solution_total_steps,
                "player_start": list(record.player_start),
                "goal": list(record.goal),
                "enemy_spawns": [
                    {
                        "type": enemy.enemy_type,
                        "cell": list(enemy.cell),
                        "move_priority": enemy.move_priority,
                        "step_count": enemy.step_count,
                        "facing_index": enemy.facing_index,
                        "traits": list(enemy.traits),
                    }
                    for enemy in record.enemy_spawns
                ],
                "teleport_pairs": [
                    {
                        "a": list(pair.a),
                        "b": list(pair.b),
                    }
                    for pair in record.teleport_pairs
                ],
            }
        )

    print(
        json.dumps(
            {
                "count": len(records),
                "duration_seconds": round(time.perf_counter() - started, 3),
                "seed_start": args.seed,
                "records": records,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
