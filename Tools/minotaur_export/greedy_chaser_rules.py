from __future__ import annotations

from dataclasses import dataclass

from .grid import MazeLayout
from .models import Coord, EnemySpec, EnemySpawn, GameState
from .movement import apply_action, available_actions

KILLER_TRAIT = "killer"
CONTACT_BLOCKED = "blocked"
CONTACT_TARGET_DIES = "target_dies"
CONTACT_MOVER_DIES = "mover_dies"


@dataclass(frozen=True, slots=True)
class GreedyChaserRules:
    minotaur_steps: int = 2
    move_priority: str = "horizontal"

    def __post_init__(self) -> None:
        if self.move_priority not in ("horizontal", "vertical"):
            raise ValueError(f"Unsupported move priority: {self.move_priority}")

    def available_actions(self, layout: MazeLayout, cell: Coord, include_skip: bool) -> list[str]:
        return available_actions(layout, cell, include_skip)

    def apply_action(self, layout: MazeLayout, cell: Coord, action: str) -> Coord:
        return apply_action(layout, cell, action)

    def move_enemy(
        self,
        layout: MazeLayout,
        player_location: Coord,
        enemy_location: Coord,
        move_priority: str | None = None,
        step_count: int | None = None,
        occupied_cells: set[Coord] | None = None,
    ) -> Coord:
        enemy = enemy_location
        active_priority = move_priority if move_priority is not None else self.move_priority
        active_step_count = step_count if step_count is not None else self.minotaur_steps
        occupied_cells = occupied_cells or set()

        for _ in range(active_step_count):
            enemy = self._choose_greedy_step(
                layout=layout,
                player_location=player_location,
                enemy_location=enemy,
                move_priority=active_priority,
                blocked_cells=occupied_cells,
            )

        return enemy

    def step_enemies(
        self,
        layout: MazeLayout,
        player_location: Coord,
        enemy_spawns: tuple[EnemySpawn, ...],
    ) -> tuple[Coord, ...] | None:
        enemy_specs = tuple(
            EnemySpec(
                enemy_type=enemy.enemy_type,
                move_priority=enemy.move_priority,
                step_count=enemy.step_count,
                traits=enemy.traits,
            )
            for enemy in enemy_spawns
        )
        next_enemy_locations = self._step_enemy_positions(
            layout=layout,
            player_location=player_location,
            enemy_positions=tuple(enemy.cell for enemy in enemy_spawns),
            enemy_specs=enemy_specs,
        )
        if next_enemy_locations is None:
            return None
        return tuple(position for position in next_enemy_locations if position is not None)

    def step_state(
        self,
        layout: MazeLayout,
        state: GameState,
        action: str,
        enemy_specs: tuple[EnemySpec, ...],
    ) -> GameState | None:
        player_location = self.apply_action(layout, state.player_position, action)
        next_enemy_locations = self._step_enemy_positions(
            layout=layout,
            player_location=player_location,
            enemy_positions=state.enemy_positions,
            enemy_specs=enemy_specs,
        )
        if next_enemy_locations is None:
            return None

        return GameState(player_position=player_location, enemy_positions=next_enemy_locations)

    def _step_enemy_positions(
        self,
        layout: MazeLayout,
        player_location: Coord,
        enemy_positions: tuple[Coord | None, ...],
        enemy_specs: tuple[EnemySpec, ...],
    ) -> tuple[Coord | None, ...] | None:
        next_enemy_locations = list(enemy_positions)

        for enemy_index, enemy_location in enumerate(next_enemy_locations):
            if enemy_location is None:
                continue

            spec = enemy_specs[enemy_index]
            for _ in range(spec.step_count):
                current_location = next_enemy_locations[enemy_index]
                if current_location is None:
                    break

                blocked_cells = self._blocked_cells_for_mover(enemy_index, next_enemy_locations, enemy_specs)
                next_enemy_location = self._choose_greedy_step(
                    layout=layout,
                    player_location=player_location,
                    enemy_location=current_location,
                    move_priority=spec.move_priority,
                    blocked_cells=blocked_cells,
                )
                if next_enemy_location == current_location:
                    continue

                target_index = self._enemy_index_at_position(next_enemy_locations, next_enemy_location, enemy_index)
                if target_index is not None:
                    contact_result = self._resolve_enemy_contact(enemy_index, target_index, enemy_specs)
                    if contact_result == CONTACT_BLOCKED:
                        continue

                    next_enemy_locations[enemy_index] = next_enemy_location
                    if contact_result == CONTACT_TARGET_DIES:
                        next_enemy_locations[target_index] = None
                    elif contact_result == CONTACT_MOVER_DIES:
                        next_enemy_locations[enemy_index] = None
                    break

                next_enemy_locations[enemy_index] = next_enemy_location
                if next_enemy_location == player_location:
                    return None

        return tuple(next_enemy_locations)

    def _choose_greedy_step(
        self,
        layout: MazeLayout,
        player_location: Coord,
        enemy_location: Coord,
        move_priority: str,
        blocked_cells: set[Coord],
    ) -> Coord:
        options = set(self.available_actions(layout, enemy_location, include_skip=False))
        options = {option for option in options if self.apply_action(layout, enemy_location, option) not in blocked_cells}

        for axis in self._preferred_axes(move_priority):
            next_cell = self._greedy_axis_step(enemy_location, player_location, axis, options)
            if next_cell != enemy_location:
                return next_cell

        return enemy_location

    def _blocked_cells_for_mover(
        self,
        mover_index: int,
        enemy_positions: list[Coord | None],
        enemy_specs: tuple[EnemySpec, ...],
    ) -> set[Coord]:
        blocked_cells: set[Coord] = set()
        for target_index, target_position in enumerate(enemy_positions):
            if target_index == mover_index or target_position is None:
                continue
            if self._resolve_enemy_contact(mover_index, target_index, enemy_specs) == CONTACT_BLOCKED:
                blocked_cells.add(target_position)
        return blocked_cells

    def _enemy_index_at_position(
        self,
        enemy_positions: list[Coord | None],
        target_position: Coord,
        excluded_index: int,
    ) -> int | None:
        for enemy_index, enemy_position in enumerate(enemy_positions):
            if enemy_index == excluded_index or enemy_position is None:
                continue
            if enemy_position == target_position:
                return enemy_index
        return None

    def _resolve_enemy_contact(
        self,
        mover_index: int,
        target_index: int,
        enemy_specs: tuple[EnemySpec, ...],
    ) -> str:
        mover_is_killer = KILLER_TRAIT in enemy_specs[mover_index].traits
        target_is_killer = KILLER_TRAIT in enemy_specs[target_index].traits

        if target_is_killer:
            if mover_is_killer and mover_index < target_index:
                return CONTACT_TARGET_DIES
            return CONTACT_MOVER_DIES

        if mover_is_killer:
            return CONTACT_TARGET_DIES

        return CONTACT_BLOCKED

    def _preferred_axes(self, move_priority: str | None = None) -> tuple[str, str]:
        active_priority = move_priority if move_priority is not None else self.move_priority
        if active_priority == "vertical":
            return ("vertical", "horizontal")
        if active_priority == "horizontal":
            return ("horizontal", "vertical")
        raise ValueError(f"Unsupported move priority: {active_priority}")

    def _greedy_axis_step(self, enemy: Coord, player_location: Coord, axis: str, options: set[str]) -> Coord:
        if axis == "horizontal":
            if "right" in options and player_location[0] > enemy[0]:
                return (enemy[0] + 1, enemy[1])
            if "left" in options and player_location[0] < enemy[0]:
                return (enemy[0] - 1, enemy[1])

        if axis == "vertical":
            if "up" in options and player_location[1] < enemy[1]:
                return (enemy[0], enemy[1] - 1)
            if "down" in options and player_location[1] > enemy[1]:
                return (enemy[0], enemy[1] + 1)

        return enemy
