from __future__ import annotations

import argparse
import json
import math
import random
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


Coord = tuple[int, int]
Edge = tuple[Coord, Coord]

DEFAULT_SOURCE_PROJECT = Path(r"C:\Users\echri\Python Projects\Minotaur-Project")
DEFAULT_OUTPUT_DIR = Path(
    r"C:\Users\echri\godotFolder\Godot_v4.5.1-stable_mono_win64\godot_v4.5.1_projects\Pharohs_Tomb\pharohs-tomb\Resources"
)

SMALL_SIZES = {(4, 4), (5, 5), (3, 5), (4, 3), (5, 3), (5, 4)}
MEDIUM_SIZES = {(6, 6), (7, 7), (7, 5)}
LARGE_SIZES = {(8, 8), (9, 9), (11, 11), (15, 11), (26, 14)}


@dataclass(frozen=True)
class MazeRecord:
    width: int
    height: int
    walls: tuple[Edge, ...]
    player_start: Coord
    minotaur_start: Coord
    goal: Coord
    solution: tuple[str, ...]
    iteration: int
    seed_hint: int | None = None

    @property
    def solution_total_steps(self) -> int:
        return len(self.solution)

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def size_category(self) -> str:
        return categorize_size(self.width, self.height)

    def signature(self) -> tuple:
        return (
            self.size,
            self.walls,
            self.player_start,
            self.minotaur_start,
            self.goal,
            self.solution,
        )


def normalize_edge(a: Coord, b: Coord) -> Edge:
    return (a, b) if a <= b else (b, a)


def build_all_edges(width: int, height: int) -> list[Edge]:
    edges: list[Edge] = []
    for y in range(height):
        for x in range(width):
            if x + 1 < width:
                edges.append(normalize_edge((x, y), (x + 1, y)))
            if y + 1 < height:
                edges.append(normalize_edge((x, y), (x, y + 1)))
    return edges


def random_cell(width: int, height: int, rng: random.Random) -> Coord:
    return (rng.randrange(width), rng.randrange(height))


def iter_neighbors(cell: Coord, width: int, height: int) -> Iterable[Coord]:
    x, y = cell
    if x > 0:
        yield (x - 1, y)
    if x + 1 < width:
        yield (x + 1, y)
    if y > 0:
        yield (x, y - 1)
    if y + 1 < height:
        yield (x, y + 1)


def is_connected(width: int, height: int, walls: set[Edge]) -> bool:
    start = (0, 0)
    queue: deque[Coord] = deque([start])
    visited = {start}

    while queue:
        current = queue.popleft()
        for nxt in iter_neighbors(current, width, height):
            if normalize_edge(current, nxt) in walls or nxt in visited:
                continue
            visited.add(nxt)
            queue.append(nxt)

    return len(visited) == width * height


def get_move_options(cell: Coord, width: int, height: int, walls: set[Edge], include_skip: bool) -> list[str]:
    options: list[str] = ["skip"] if include_skip else []
    x, y = cell
    candidates = (
        ("right", (x + 1, y)),
        ("left", (x - 1, y)),
        ("up", (x, y - 1)),
        ("down", (x, y + 1)),
    )

    for action, nxt in candidates:
        nx_, ny_ = nxt
        if nx_ < 0 or ny_ < 0 or nx_ >= width or ny_ >= height:
            continue
        if normalize_edge(cell, nxt) in walls:
            continue
        options.append(action)

    return options


def apply_action(cell: Coord, action: str, width: int, height: int, walls: set[Edge]) -> Coord:
    x, y = cell
    if action == "skip":
        return cell
    offsets = {
        "right": (1, 0),
        "left": (-1, 0),
        "up": (0, -1),
        "down": (0, 1),
    }
    if action not in offsets:
        return cell
    dx, dy = offsets[action]
    nxt = (x + dx, y + dy)
    nx_, ny_ = nxt
    if nx_ < 0 or ny_ < 0 or nx_ >= width or ny_ >= height:
        return cell
    if normalize_edge(cell, nxt) in walls:
        return cell
    return nxt


def move_minotaur(player_location: Coord, minotaur_location: Coord, width: int, height: int, walls: set[Edge]) -> Coord:
    mino = minotaur_location
    for _ in range(2):
        options = set(get_move_options(mino, width, height, walls, include_skip=False))

        if "right" in options and player_location[0] > mino[0]:
            mino = (mino[0] + 1, mino[1])
            continue
        if "left" in options and player_location[0] < mino[0]:
            mino = (mino[0] - 1, mino[1])
            continue
        if "up" in options and player_location[1] < mino[1]:
            mino = (mino[0], mino[1] - 1)
            continue
        if "down" in options and player_location[1] > mino[1]:
            mino = (mino[0], mino[1] + 1)
            continue

    return mino


def solve_maze(width: int, height: int, walls: set[Edge], player_start: Coord, minotaur_start: Coord, goal: Coord) -> tuple[bool, list[str]]:
    current_state = (player_start, minotaur_start)
    move_queue: deque[tuple[str, tuple[Coord, Coord], list[str]]] = deque()
    for option in get_move_options(player_start, width, height, walls, include_skip=True):
        move_queue.append((option, current_state, []))

    visited: set[tuple[str, tuple[Coord, Coord]]] = set()

    while move_queue:
        option, state, moves = move_queue.popleft()
        if (option, state) in visited:
            continue
        visited.add((option, state))

        player_location, minotaur_location = state
        player_location = apply_action(player_location, option, width, height, walls)
        minotaur_location = move_minotaur(player_location, minotaur_location, width, height, walls)

        if minotaur_location == player_location:
            continue

        next_moves = moves + [option]
        if player_location == goal:
            return True, next_moves

        next_state = (player_location, minotaur_location)
        for next_option in get_move_options(player_location, width, height, walls, include_skip=True):
            move_queue.append((next_option, next_state, next_moves))

    return False, []


def generate_batch(
    width: int,
    height: int,
    min_moves: int,
    target_count: int,
    rng: random.Random,
    iteration: int,
    additional_checks: bool,
    additional_check_threshold: int,
) -> list[MazeRecord]:
    generated: list[MazeRecord] = []
    seen_signatures: set[tuple] = set()
    all_edges = build_all_edges(width, height)
    largest_solution = 0
    board_seed = 0

    while len(generated) < target_count:
        walls_remaining = list(all_edges)
        open_edges: set[Edge] = set()

        minimum_open_edges = width * height
        for _ in range(minimum_open_edges):
            edge = walls_remaining.pop(rng.randrange(len(walls_remaining)))
            open_edges.add(edge)

        while not is_connected(width, height, set(walls_remaining)):
            edge = walls_remaining.pop(rng.randrange(len(walls_remaining)))
            open_edges.add(edge)

        while len(walls_remaining) > max(width, height):
            checks_remaining = len(walls_remaining)

            while checks_remaining > 0:
                checks_remaining -= 1

                while True:
                    player_start = random_cell(width, height, rng)
                    minotaur_start = random_cell(width, height, rng)
                    goal = random_cell(width, height, rng)
                    if player_start != goal and player_start != minotaur_start:
                        break

                walls = set(walls_remaining)
                solvable, solution = solve_maze(width, height, walls, player_start, minotaur_start, goal)
                if not solvable or len(solution) < min_moves:
                    continue

                normalized_walls = tuple(sorted(walls, key=edge_sort_key))
                record = MazeRecord(
                    width=width,
                    height=height,
                    walls=normalized_walls,
                    player_start=player_start,
                    minotaur_start=minotaur_start,
                    goal=goal,
                    solution=tuple(solution),
                    iteration=iteration,
                    seed_hint=board_seed,
                )
                signature = record.signature()
                if signature in seen_signatures:
                    continue

                seen_signatures.add(signature)
                generated.append(record)
                if record.solution_total_steps >= largest_solution:
                    largest_solution = record.solution_total_steps
                    if additional_checks and largest_solution >= additional_check_threshold:
                        checks_remaining += largest_solution * largest_solution

                if len(generated) >= target_count:
                    return generated

            removed_wall = walls_remaining.pop(rng.randrange(len(walls_remaining)))
            open_edges.add(removed_wall)

        board_seed += 1

    return generated


def categorize_size(width: int, height: int) -> str:
    size = (width, height)
    if size in SMALL_SIZES:
        return "small"
    if size in MEDIUM_SIZES:
        return "medium"
    if size in LARGE_SIZES or max(width, height) >= 8:
        return "large"
    if max(width, height) >= 6:
        return "medium"
    return "small"


def assign_difficulty_labels(records: list[MazeRecord]) -> dict[MazeRecord, str]:
    grouped: dict[tuple[int, int], list[MazeRecord]] = {}
    for record in records:
        grouped.setdefault(record.size, []).append(record)

    labels: dict[MazeRecord, str] = {}
    for _, group in grouped.items():
        ordered = sorted(group, key=lambda item: item.solution_total_steps)
        top_length = ordered[-1].solution_total_steps
        for index, record in enumerate(ordered):
            if record.solution_total_steps == top_length:
                labels[record] = "max"
                continue

            percentile = (index + 1) / max(len(ordered), 1)
            if percentile <= (1.0 / 3.0):
                labels[record] = "easy"
            elif percentile <= (2.0 / 3.0):
                labels[record] = "medium"
            else:
                labels[record] = "hard"

    return labels


def edge_sort_key(edge: Edge) -> tuple[int, int, int, int]:
    (ax, ay), (bx, by) = edge
    return (ay, ax, by, bx)


def to_horizontal_vertical_walls(walls: Iterable[Edge]) -> tuple[list[Coord], list[Coord]]:
    horizontal: list[Coord] = []
    vertical: list[Coord] = []
    for a, b in walls:
        if a[0] != b[0]:
            vertical.append((max(a[0], b[0]), a[1]))
        else:
            horizontal.append((a[0], max(a[1], b[1])))

    horizontal.sort(key=lambda item: (item[1], item[0]))
    vertical.sort(key=lambda item: (item[1], item[0]))
    return horizontal, vertical


def vector2i(value: Coord) -> str:
    return f"Vector2i({value[0]}, {value[1]})"


def vector2i_array(values: Iterable[Coord]) -> str:
    serialized = ", ".join(vector2i(value) for value in values)
    return f"Array[Vector2i]([{serialized}])"


def string_array(values: Iterable[str]) -> str:
    serialized = ", ".join(json.dumps(value) for value in values)
    return f"Array[String]([{serialized}])"


def build_display_name(saved_at_unix: int, width: int, height: int, difficulty_label: str, index: int) -> str:
    stamp = datetime.fromtimestamp(saved_at_unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"{stamp} {width}x{height} {difficulty_label.capitalize()} #{index:03d}"


def build_file_name(saved_at_unix: int, width: int, height: int, steps: int, difficulty_label: str, index: int) -> str:
    stamp = datetime.fromtimestamp(saved_at_unix, tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"minotaur_{stamp}_{width}x{height}_len{steps:03d}_{difficulty_label}_{index:03d}.tres"


def serialize_tres(record: MazeRecord, saved_at_unix: int, difficulty_label: str, index: int, generation_profile_id: str) -> str:
    horizontal_walls, vertical_walls = to_horizontal_vertical_walls(record.walls)
    display_name = build_display_name(saved_at_unix, record.width, record.height, difficulty_label, index)

    lines = [
        '[gd_resource type="Resource" script_class="SavedMazeResource" load_steps=2 format=3]',
        "",
        '[ext_resource type="Script" path="res://MazeGenerator/saved_maze_resource.gd" id="1_hji17"]',
        "",
        "[resource]",
        'script = ExtResource("1_hji17")',
        f"display_name = {json.dumps(display_name)}",
        f"saved_at_unix = {saved_at_unix}",
        f"width = {record.width}",
        f"height = {record.height}",
        f"size_category = {json.dumps(record.size_category)}",
        f"difficulty_category = {json.dumps(difficulty_label)}",
        f"horizontal_walls = {vector2i_array(horizontal_walls)}",
        f"vertical_walls = {vector2i_array(vertical_walls)}",
        f"player_spawn = {vector2i(record.player_start)}",
        f"minotaur_spawn = {vector2i(record.minotaur_start)}",
        f"exit_cell = {vector2i(record.goal)}",
        f"solution_actions = {string_array(record.solution)}",
        f"solution_total_steps = {record.solution_total_steps}",
        'generation_mode = "IMPORTED_MINOTAUR_PROJECT"',
        f"generation_profile_id = {json.dumps(generation_profile_id)}",
        "",
    ]
    return "\n".join(lines)


def write_manifest(
    manifest_path: Path,
    source_project: Path,
    output_dir: Path,
    args: argparse.Namespace,
    generated_records: list[tuple[Path, MazeRecord, str]],
) -> None:
    manifest = {
        "source_project": str(source_project),
        "output_dir": str(output_dir),
        "generated_at_unix": int(time.time()),
        "parameters": {
            "width": args.width,
            "height": args.height,
            "iterations": args.iterations,
            "mazes_per_iteration": args.mazes_per_iteration,
            "min_moves": args.min_moves,
            "seed": args.seed,
            "cell_size": args.cell_size,
            "additional_checks": args.additional_checks,
            "additional_check_threshold": args.additional_check_threshold,
        },
        "files": [
            {
                "file_name": path.name,
                "path": str(path),
                "width": record.width,
                "height": record.height,
                "solution_total_steps": record.solution_total_steps,
                "difficulty_category": difficulty_label,
                "iteration": record.iteration,
                "player_start": list(record.player_start),
                "minotaur_start": list(record.minotaur_start),
                "goal": list(record.goal),
            }
            for path, record, difficulty_label in generated_records
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
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
    parser.add_argument("--additional-check-threshold", type=int, default=50)
    parser.add_argument("--additional-checks", dest="additional_checks", action="store_true")
    parser.add_argument("--no-additional-checks", dest="additional_checks", action="store_false")
    parser.set_defaults(additional_checks=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    all_records: list[MazeRecord] = []

    print(f"Source project: {args.source_project}")
    print(f"Output directory: {output_dir}")
    print(
        "Generating mazes with width=%d height=%d iterations=%d mazes_per_iteration=%d min_moves=%d seed=%s"
        % (
            args.width,
            args.height,
            args.iterations,
            args.mazes_per_iteration,
            args.min_moves,
            args.seed if args.seed is not None else "random",
        )
    )

    for iteration in range(1, args.iterations + 1):
        print(f"Iteration {iteration}/{args.iterations}: generating solvable mazes...")
        batch = generate_batch(
            width=args.width,
            height=args.height,
            min_moves=args.min_moves,
            target_count=args.mazes_per_iteration,
            rng=rng,
            iteration=iteration,
            additional_checks=args.additional_checks,
            additional_check_threshold=args.additional_check_threshold,
        )
        all_records.extend(batch)
        print(f"Iteration {iteration}/{args.iterations}: exported {len(batch)} solvable mazes.")

    difficulty_labels = assign_difficulty_labels(all_records)
    generation_profile_id = f"minotaur_import_{args.width}x{args.height}_batch"
    saved_at_unix = int(time.time())
    generated_records: list[tuple[Path, MazeRecord, str]] = []

    for index, record in enumerate(
        sorted(all_records, key=lambda item: (item.iteration, item.solution_total_steps, item.goal, item.player_start, item.minotaur_start)),
        start=1,
    ):
        difficulty_label = difficulty_labels[record]
        file_name = build_file_name(
            saved_at_unix=saved_at_unix,
            width=record.width,
            height=record.height,
            steps=record.solution_total_steps,
            difficulty_label=difficulty_label,
            index=index,
        )
        file_path = output_dir / file_name
        file_path.write_text(
            serialize_tres(
                record=record,
                saved_at_unix=saved_at_unix + index - 1,
                difficulty_label=difficulty_label,
                index=index,
                generation_profile_id=generation_profile_id,
            ),
            encoding="utf-8",
        )
        generated_records.append((file_path, record, difficulty_label))

    manifest_name = datetime.now().strftime("minotaur_export_manifest_%Y%m%d_%H%M%S.json")
    manifest_path = output_dir / manifest_name
    write_manifest(
        manifest_path=manifest_path,
        source_project=args.source_project,
        output_dir=output_dir,
        args=args,
        generated_records=generated_records,
    )

    print(f"Wrote {len(generated_records)} maze resources.")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
