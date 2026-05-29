from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


Coord = tuple[int, int]
Edge = tuple[Coord, Coord]

SMALL_SIZES = {(4, 4), (5, 5), (3, 5), (4, 3), (5, 3), (5, 4)}
MEDIUM_SIZES = {(6, 6), (7, 7), (7, 5)}
LARGE_SIZES = {(8, 8), (9, 9), (11, 11), (15, 11), (26, 14)}


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


@dataclass(frozen=True, slots=True)
class GameState:
    player_position: Coord
    enemy_positions: tuple[Coord | None, ...]
    enemy_states: tuple["EnemyRuntimeState", ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class EnemyRuntimeState:
    facing_index: int = 2
    attack_phase: int = -1
    turns_until_dash: int = 0


@dataclass(frozen=True, slots=True)
class TeleportPair:
    a: Coord
    b: Coord

    def normalized(self) -> "TeleportPair":
        if self.a <= self.b:
            return self
        return TeleportPair(self.b, self.a)


@dataclass(frozen=True, slots=True)
class SolveResult:
    solvable: bool
    actions: tuple[str, ...]

    @property
    def total_steps(self) -> int:
        return len(self.actions)


@dataclass(frozen=True, slots=True)
class MazeRecord:
    width: int
    height: int
    walls: tuple[Edge, ...]
    trap_cells: tuple[Coord, ...]
    player_start: Coord
    enemy_spawns: tuple["EnemySpawn", ...]
    goal: Coord
    solution: tuple[str, ...]
    iteration: int
    teleport_pairs: tuple[TeleportPair, ...] = ()
    enemy_teleport_pairs: tuple[TeleportPair, ...] = ()
    shared_teleport_pairs: tuple[TeleportPair, ...] = ()
    seed_hint: int | None = None

    @property
    def solution_total_steps(self) -> int:
        return len(self.solution)

    @property
    def minotaur_start(self) -> Coord:
        if not self.enemy_spawns:
            return (0, 0)
        return self.enemy_spawns[0].cell

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
            self.teleport_pairs,
            self.enemy_teleport_pairs,
            self.shared_teleport_pairs,
            self.trap_cells,
            self.player_start,
            self.enemy_spawns,
            self.goal,
            self.solution,
        )


@dataclass(frozen=True, slots=True)
class EnemySpec:
    enemy_type: str = "greedy_chaser"
    move_priority: str = "horizontal"
    step_count: int = 2
    facing_index: int = 2
    traits: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EnemySpawn:
    enemy_type: str
    cell: Coord
    move_priority: str
    step_count: int = 2
    facing_index: int = 2
    traits: tuple[str, ...] = ()

    @classmethod
    def from_spec(cls, spec: EnemySpec, cell: Coord) -> "EnemySpawn":
        return cls(
            enemy_type=spec.enemy_type,
            cell=cell,
            move_priority=spec.move_priority,
            step_count=spec.step_count,
            facing_index=spec.facing_index,
            traits=spec.traits,
        )


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    source_project: Path
    output_dir: Path
    width: int = 9
    height: int = 9
    iterations: int = 10
    mazes_per_iteration: int = 10
    min_moves: int = 30
    seed: int | None = None
    cell_size: int = 16
    enemy_move_priority: str = "horizontal"
    greedy_horizontal_count: int = 1
    greedy_vertical_count: int = 0
    samurai_count: int = 0
    killer_count: int = 0
    trap_count: int = 0
    additional_check_threshold: int = 50
    additional_checks: bool = True

    @property
    def generation_profile_id(self) -> str:
        return (
            f"greedy_enemies_{self.greedy_horizontal_count}x_{self.greedy_vertical_count}y_"
            f"{self.samurai_count}samurai_"
            f"{self.killer_count}killer_{self.trap_count}traps_{self.width}x{self.height}_batch"
        )

    @property
    def enemy_specs(self) -> tuple[EnemySpec, ...]:
        specs: list[EnemySpec] = []
        specs.extend(EnemySpec(move_priority="horizontal") for _ in range(self.greedy_horizontal_count))
        specs.extend(EnemySpec(move_priority="vertical") for _ in range(self.greedy_vertical_count))
        specs.extend(EnemySpec(enemy_type="samurai", step_count=1, facing_index=2) for _ in range(self.samurai_count))
        specs = [
            EnemySpec(
                enemy_type=spec.enemy_type,
                move_priority=spec.move_priority,
                step_count=spec.step_count,
                facing_index=spec.facing_index,
                traits=("killer",) if index < self.killer_count else (),
            )
            for index, spec in enumerate(specs)
        ]
        return tuple(specs)


@dataclass(frozen=True, slots=True)
class ExportedMaze:
    path: Path
    record: MazeRecord
    difficulty_label: str


@dataclass(frozen=True, slots=True)
class ExportSummary:
    exported_mazes: tuple[ExportedMaze, ...]
    manifest_path: Path
