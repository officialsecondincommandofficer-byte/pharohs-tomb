from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


Coord = tuple[int, int]
Edge = tuple[Coord, Coord]
DirectedEdge = tuple[Coord, Coord]

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
    spawned_enemies: tuple["SpawnedEnemyState", ...] = field(default_factory=tuple)
    spawner_states: tuple["ZoneSpawnerState", ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SamuraiBehaviorState:
    facing_index: int = 2
    attack_phase: int = -1
    turns_until_dash: int = 0


@dataclass(frozen=True, slots=True)
class AStarBehaviorState:
    path_version: int = 0


BehaviorState = SamuraiBehaviorState | AStarBehaviorState | None


@dataclass(frozen=True, slots=True)
class EnemyRuntimeState:
    activated: bool = True
    turns_remaining: int = -1
    turns_until_spawn: int = 0
    behavior_state: BehaviorState = None


@dataclass(frozen=True, slots=True)
class SpawnedEnemyState:
    spec: "EnemySpec"
    position: Coord | None
    runtime_state: EnemyRuntimeState
    source_spawner_id: str = ""


@dataclass(frozen=True, slots=True)
class ZoneSpawnerState:
    turns_until_spawn: int


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
    goal_cells: tuple[Coord, ...] = ()
    escape_zone_cells: tuple[Coord, ...] = ()
    zone_spawners: tuple["ZoneSpawnerSpec", ...] = ()
    player_only_walls: tuple[Edge, ...] = ()
    enemy_only_walls: tuple[Edge, ...] = ()
    one_way_passages: tuple[DirectedEdge, ...] = ()
    teleport_pairs: tuple[TeleportPair, ...] = ()
    enemy_teleport_pairs: tuple[TeleportPair, ...] = ()
    shared_teleport_pairs: tuple[TeleportPair, ...] = ()
    seed_hint: int | None = None

    @property
    def solution_total_steps(self) -> int:
        return len(self.solution)

    @property
    def resolved_goal_cells(self) -> tuple[Coord, ...]:
        if self.goal_cells:
            return self.goal_cells
        return (self.goal,)

    @property
    def main_exit_cell(self) -> Coord:
        return self.goal

    @property
    def main_exit_cells(self) -> tuple[Coord, ...]:
        if self.goal_cells:
            return tuple(cell for cell in self.goal_cells if cell not in self.escape_zone_cells) or (self.goal,)
        return (self.goal,)

    @property
    def win_zone_cells(self) -> tuple[Coord, ...]:
        return self.resolved_goal_cells

    @property
    def escape_zone_spawners(self) -> tuple["ZoneSpawnerSpec", ...]:
        return self.zone_spawners

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
            self.player_only_walls,
            self.enemy_only_walls,
            self.one_way_passages,
            self.teleport_pairs,
            self.enemy_teleport_pairs,
            self.shared_teleport_pairs,
            self.trap_cells,
            self.player_start,
            self.enemy_spawns,
            self.goal,
            self.goal_cells,
            self.escape_zone_cells,
            self.zone_spawners,
            self.solution,
        )


@dataclass(frozen=True, slots=True)
class EnemySpec:
    enemy_type: str = "greedy_chaser"
    role: str = ""
    movement_type: str = ""
    move_priority: str = "horizontal"
    step_count: int = 2
    facing_index: int = 2
    traits: tuple[str, ...] = ()
    wake_goal_distance: int = -1
    lifetime_turns: int = -1
    spawn_delay_turns: int = 0
    respawn_delay_turns: int = 0
    spawn_cell: Coord | None = None


@dataclass(frozen=True, slots=True)
class EnemySpawn:
    enemy_type: str
    cell: Coord
    move_priority: str
    role: str = ""
    movement_type: str = ""
    step_count: int = 2
    facing_index: int = 2
    traits: tuple[str, ...] = ()
    wake_goal_distance: int = -1
    lifetime_turns: int = -1
    spawn_delay_turns: int = 0
    respawn_delay_turns: int = 0

    @classmethod
    def from_spec(cls, spec: EnemySpec, cell: Coord) -> "EnemySpawn":
        return cls(
            enemy_type=spec.enemy_type,
            cell=cell,
            move_priority=spec.move_priority,
            role=spec.role,
            movement_type=spec.movement_type,
            step_count=spec.step_count,
            facing_index=spec.facing_index,
            traits=spec.traits,
            wake_goal_distance=spec.wake_goal_distance,
            lifetime_turns=spec.lifetime_turns,
            spawn_delay_turns=spec.spawn_delay_turns,
            respawn_delay_turns=spec.respawn_delay_turns,
        )


@dataclass(frozen=True, slots=True)
class ZoneSpawnerSpec:
    spawner_id: str
    enemy_spec: EnemySpec
    spawn_interval_turns: int
    spawn_candidates: tuple[Coord, ...]
    source_zone_cells: tuple[Coord, ...] = ()
    initial_delay_turns: int = -1


def resolved_enemy_role(
    enemy_type: str,
    move_priority: str = "horizontal",
    traits: tuple[str, ...] = (),
    explicit_role: str = "",
) -> str:
    if explicit_role:
        return explicit_role
    if enemy_type in ("dasher", "samurai"):
        return "dasher"
    if enemy_type == "linked_escape_hunter":
        return "linked_escape_hunter"
    if enemy_type == "astar_chaser" or "escape_linked" in traits:
        return "linked_escape_hunter"
    if enemy_type in ("x_chaser", "y_chaser"):
        return enemy_type
    if enemy_type in ("chaser", "greedy_chaser", "minotaur"):
        return "y_chaser" if move_priority == "vertical" else "x_chaser"
    return enemy_type


def resolved_movement_type(
    enemy_type: str,
    role: str = "",
    explicit_movement_type: str = "",
) -> str:
    if explicit_movement_type:
        return explicit_movement_type
    resolved_role = role or enemy_type
    if resolved_role == "linked_escape_hunter" or enemy_type == "astar_chaser":
        return "astar"
    if resolved_role in ("x_chaser", "y_chaser", "chaser", "minotaur"):
        return "greedy"
    if resolved_role in ("dasher", "samurai"):
        return "dash"
    if resolved_role == "patroller":
        return "patrol"
    if resolved_role == "wanderer":
        return "wander"
    return "greedy"


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
    player_only_wall_count: int = 0
    enemy_only_wall_count: int = 0
    one_way_passage_count: int = 0
    additional_check_threshold: int = 50
    additional_checks: bool = True

    @property
    def generation_profile_id(self) -> str:
        return (
            f"greedy_enemies_{self.greedy_horizontal_count}x_{self.greedy_vertical_count}y_"
            f"{self.samurai_count}samurai_"
            f"{self.killer_count}killer_{self.trap_count}traps_"
            f"{self.player_only_wall_count}playerwalls_{self.enemy_only_wall_count}enemywalls_"
            f"{self.one_way_passage_count}oneways_"
            f"{self.width}x{self.height}_batch"
        )

    @property
    def enemy_specs(self) -> tuple[EnemySpec, ...]:
        specs: list[EnemySpec] = []
        specs.extend(EnemySpec(role="x_chaser", movement_type="greedy", move_priority="horizontal") for _ in range(self.greedy_horizontal_count))
        specs.extend(EnemySpec(role="y_chaser", movement_type="greedy", move_priority="vertical") for _ in range(self.greedy_vertical_count))
        specs.extend(EnemySpec(enemy_type="samurai", role="dasher", movement_type="dash", step_count=1, facing_index=2) for _ in range(self.samurai_count))
        specs = [
            EnemySpec(
                enemy_type=spec.enemy_type,
                role=spec.role,
                movement_type=spec.movement_type,
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
