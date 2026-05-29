from __future__ import annotations

from dataclasses import dataclass

from .grid import MazeLayout
from .models import Coord, EnemyRuntimeState, EnemySpec, EnemySpawn, GameState
from .movement import apply_action, available_actions, resolve_enemy_turn_end_transition, resolve_player_action, resolve_player_transition, resolve_player_turn_end_transition

KILLER_TRAIT = "killer"
CONTACT_BLOCKED = "blocked"
CONTACT_TARGET_DIES = "target_dies"
CONTACT_MOVER_DIES = "mover_dies"
SAMURAI_ROTATIONS: tuple[Coord, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))
SAMURAI_CHARGE_DELAYS: tuple[int, ...] = (3, 2, 1)


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

    def resolve_player_action(self, layout: MazeLayout, cell: Coord, action: str) -> Coord:
        return resolve_player_action(layout, cell, action)

    def resolve_player_transition(self, layout: MazeLayout, cell: Coord, action: str):
        return resolve_player_transition(layout, cell, action)

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

        enemy = resolve_enemy_turn_end_transition(layout, enemy).resolved_cell

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
                facing_index=enemy.facing_index,
                traits=enemy.traits,
            )
            for enemy in enemy_spawns
        )
        next_enemy_locations, _ = self._step_enemy_positions(
            layout=layout,
            player_location=player_location,
            enemy_positions=tuple(enemy.cell for enemy in enemy_spawns),
            enemy_states=tuple(EnemyRuntimeState(facing_index=enemy.facing_index) for enemy in enemy_spawns),
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
        transition = self.resolve_player_transition(layout, state.player_position, action)
        next_enemy_locations, next_enemy_states = self._step_enemy_positions(
            layout=layout,
            player_location=transition.stepped_cell,
            enemy_positions=state.enemy_positions,
            enemy_states=state.enemy_states,
            enemy_specs=enemy_specs,
        )
        if next_enemy_locations is None:
            return None

        turn_end_transition = resolve_player_turn_end_transition(layout, transition.resolved_cell)

        return GameState(
            player_position=turn_end_transition.resolved_cell,
            enemy_positions=next_enemy_locations,
            enemy_states=next_enemy_states,
        )

    def _step_enemy_positions(
        self,
        layout: MazeLayout,
        player_location: Coord,
        enemy_positions: tuple[Coord | None, ...],
        enemy_states: tuple[EnemyRuntimeState, ...],
        enemy_specs: tuple[EnemySpec, ...],
    ) -> tuple[tuple[Coord | None, ...] | None, tuple[EnemyRuntimeState, ...]]:
        next_enemy_locations = list(enemy_positions)
        next_enemy_states = list(enemy_states)

        for enemy_index, enemy_location in enumerate(next_enemy_locations):
            if enemy_location is None:
                continue

            spec = enemy_specs[enemy_index]
            if spec.enemy_type == "samurai":
                caught_player = self._step_samurai(
                    layout=layout,
                    player_location=player_location,
                    enemy_index=enemy_index,
                    enemy_positions=next_enemy_locations,
                    enemy_states=next_enemy_states,
                    enemy_specs=enemy_specs,
                )
                if caught_player:
                    return None, tuple(next_enemy_states)
                continue

            caught_player = self._step_greedy_enemy(
                layout=layout,
                player_location=player_location,
                enemy_index=enemy_index,
                enemy_positions=next_enemy_locations,
                enemy_specs=enemy_specs,
                move_priority=spec.move_priority,
                step_count=spec.step_count,
            )
            if caught_player:
                return None, tuple(next_enemy_states)

        if any(enemy_location == player_location for enemy_location in next_enemy_locations if enemy_location is not None):
            return None, tuple(next_enemy_states)

        return tuple(next_enemy_locations), tuple(next_enemy_states)

    def _step_greedy_enemy(
        self,
        layout: MazeLayout,
        player_location: Coord,
        enemy_index: int,
        enemy_positions: list[Coord | None],
        enemy_specs: tuple[EnemySpec, ...],
        move_priority: str,
        step_count: int,
    ) -> bool:
        final_location: Coord | None = None
        for _ in range(step_count):
            current_location = enemy_positions[enemy_index]
            if current_location is None:
                break

            blocked_cells = self._blocked_cells_for_mover(enemy_index, enemy_positions, enemy_specs)
            next_enemy_location = self._choose_greedy_step(
                layout=layout,
                player_location=player_location,
                enemy_location=current_location,
                move_priority=move_priority,
                blocked_cells=blocked_cells,
            )
            if next_enemy_location == current_location:
                continue

            caught_player = self._move_enemy_to_target(
                player_location=player_location,
                enemy_index=enemy_index,
                enemy_positions=enemy_positions,
                enemy_specs=enemy_specs,
                next_enemy_location=next_enemy_location,
            )
            if caught_player:
                return True
            if enemy_positions[enemy_index] is None:
                break
            final_location = enemy_positions[enemy_index]

        if final_location is None:
            final_location = enemy_positions[enemy_index]
        if final_location is None:
            return False

        turn_end_transition = resolve_enemy_turn_end_transition(layout, final_location)
        if not turn_end_transition.used_teleport:
            return False

        return self._move_enemy_to_target(
            player_location=player_location,
            enemy_index=enemy_index,
            enemy_positions=enemy_positions,
            enemy_specs=enemy_specs,
            next_enemy_location=turn_end_transition.resolved_cell,
        )

    def _step_samurai(
        self,
        layout: MazeLayout,
        player_location: Coord,
        enemy_index: int,
        enemy_positions: list[Coord | None],
        enemy_states: list[EnemyRuntimeState],
        enemy_specs: tuple[EnemySpec, ...],
    ) -> bool:
        current_location = enemy_positions[enemy_index]
        if current_location is None:
            return False

        state = enemy_states[enemy_index]
        if state.attack_phase == -1:
            rotated_facing = (state.facing_index + 1) % len(SAMURAI_ROTATIONS)
            updated_state = EnemyRuntimeState(facing_index=rotated_facing)
            if self._samurai_can_see_player(current_location, player_location, rotated_facing):
                updated_state = EnemyRuntimeState(
                    facing_index=rotated_facing,
                    attack_phase=0,
                    turns_until_dash=SAMURAI_CHARGE_DELAYS[0],
                )
            enemy_states[enemy_index] = updated_state
            return False

        turns_until_dash = state.turns_until_dash - 1
        if turns_until_dash > 0:
            enemy_states[enemy_index] = EnemyRuntimeState(
                facing_index=state.facing_index,
                attack_phase=state.attack_phase,
                turns_until_dash=turns_until_dash,
            )
            return False

        blocked_cells = self._blocked_cells_for_mover(enemy_index, enemy_positions, enemy_specs)
        next_enemy_location = self._choose_samurai_dash_target(
            player_location=player_location,
            enemy_location=current_location,
            facing_index=state.facing_index,
            blocked_cells=blocked_cells,
        )
        enemy_states[enemy_index] = self._advance_samurai_state(state)
        if next_enemy_location == current_location:
            return False
        caught_player = self._move_enemy_to_target(
            player_location=player_location,
            enemy_index=enemy_index,
            enemy_positions=enemy_positions,
            enemy_specs=enemy_specs,
            next_enemy_location=next_enemy_location,
        )
        if caught_player:
            return True

        current_location = enemy_positions[enemy_index]
        if current_location is None:
            return False

        turn_end_transition = resolve_enemy_turn_end_transition(layout, current_location)
        if not turn_end_transition.used_teleport:
            return False

        return self._move_enemy_to_target(
            player_location=player_location,
            enemy_index=enemy_index,
            enemy_positions=enemy_positions,
            enemy_specs=enemy_specs,
            next_enemy_location=turn_end_transition.resolved_cell,
        )

    def _move_enemy_to_target(
        self,
        player_location: Coord,
        enemy_index: int,
        enemy_positions: list[Coord | None],
        enemy_specs: tuple[EnemySpec, ...],
        next_enemy_location: Coord,
    ) -> bool:
        current_location = enemy_positions[enemy_index]
        if current_location is None or next_enemy_location == current_location:
            return False

        target_index = self._enemy_index_at_position(enemy_positions, next_enemy_location, enemy_index)
        if target_index is not None:
            contact_result = self._resolve_enemy_contact(enemy_index, target_index, enemy_specs)
            if contact_result == CONTACT_BLOCKED:
                return False

            enemy_positions[enemy_index] = next_enemy_location
            if contact_result == CONTACT_TARGET_DIES:
                enemy_positions[target_index] = None
            elif contact_result == CONTACT_MOVER_DIES:
                enemy_positions[enemy_index] = None
            return False

        enemy_positions[enemy_index] = next_enemy_location
        return next_enemy_location == player_location

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

    def _samurai_can_see_player(self, enemy_location: Coord, player_location: Coord, facing_index: int) -> bool:
        delta_x = player_location[0] - enemy_location[0]
        delta_y = player_location[1] - enemy_location[1]
        facing_x, facing_y = SAMURAI_ROTATIONS[facing_index]

        if facing_x != 0:
            return delta_y == 0 and delta_x != 0 and (1 if delta_x > 0 else -1) == facing_x
        return delta_x == 0 and delta_y != 0 and (1 if delta_y > 0 else -1) == facing_y

    def _choose_samurai_dash_target(
        self,
        player_location: Coord,
        enemy_location: Coord,
        facing_index: int,
        blocked_cells: set[Coord],
    ) -> Coord:
        delta_x = player_location[0] - enemy_location[0]
        delta_y = player_location[1] - enemy_location[1]
        if delta_x == 0 and delta_y == 0:
            return enemy_location

        use_vertical = abs(delta_y) > abs(delta_x)
        if abs(delta_x) == abs(delta_y):
            _, facing_y = SAMURAI_ROTATIONS[facing_index]
            use_vertical = facing_y != 0 and delta_y != 0

        if use_vertical and delta_y != 0:
            target = (enemy_location[0], player_location[1])
        elif delta_x != 0:
            target = (player_location[0], enemy_location[1])
        else:
            target = (enemy_location[0], player_location[1])

        if target in blocked_cells:
            return enemy_location
        return target

    def _advance_samurai_state(self, state: EnemyRuntimeState) -> EnemyRuntimeState:
        next_phase = state.attack_phase + 1
        if next_phase >= len(SAMURAI_CHARGE_DELAYS):
            return EnemyRuntimeState(facing_index=state.facing_index)
        return EnemyRuntimeState(
            facing_index=state.facing_index,
            attack_phase=next_phase,
            turns_until_dash=SAMURAI_CHARGE_DELAYS[next_phase],
        )
