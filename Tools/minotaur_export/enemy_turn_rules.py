from __future__ import annotations

from dataclasses import dataclass, field, replace

from .astar_chaser_rules import AStarChaserBehavior
from .enemy_activation_rules import advance_lifetime, update_activation_state
from .enemy_behavior import EnemyBehavior
from .enemy_contact_rules import (
    CONTACT_BLOCKED,
    CONTACT_MOVER_DIES,
    CONTACT_TARGET_DIES,
    blocked_cells_for_mover,
    enemy_index_at_position,
    resolve_enemy_contact,
)
from .enemy_spawn_rules import advance_spawn_state
from .greedy_chaser_rules import GreedyChaserBehavior, choose_greedy_step
from .grid import MazeLayout
from .models import (
    Coord,
    EnemyRuntimeState,
    EnemySpec,
    EnemySpawn,
    GameState,
    SpawnedEnemyState,
    ZoneSpawnerSpec,
    resolved_movement_type,
)
from .movement import (
    apply_action,
    apply_enemy_action,
    available_actions,
    available_enemy_actions,
    resolve_enemy_turn_end_transition,
    resolve_player_action,
    resolve_player_transition,
    resolve_player_turn_end_transition,
)
from .samurai_rules import SamuraiBehavior
from .zone_spawner_rules import advance_zone_spawner


def build_default_enemy_behaviors() -> dict[str, EnemyBehavior]:
    greedy = GreedyChaserBehavior()
    return {
        "greedy": greedy,
        "astar": AStarChaserBehavior(),
        "dash": SamuraiBehavior(),
    }


@dataclass(frozen=True, slots=True)
class EnemyTurnRules:
    minotaur_steps: int = 2
    move_priority: str = "horizontal"
    behavior_registry: dict[str, EnemyBehavior] = field(default_factory=build_default_enemy_behaviors)

    def __post_init__(self) -> None:
        if self.move_priority not in ("horizontal", "vertical"):
            raise ValueError(f"Unsupported move priority: {self.move_priority}")

    def available_actions(self, layout: MazeLayout, cell: Coord, include_skip: bool) -> list[str]:
        return available_actions(layout, cell, include_skip)

    def available_enemy_actions(self, layout: MazeLayout, cell: Coord, include_skip: bool) -> list[str]:
        return available_enemy_actions(layout, cell, include_skip)

    def apply_action(self, layout: MazeLayout, cell: Coord, action: str) -> Coord:
        return apply_action(layout, cell, action)

    def apply_enemy_action(self, layout: MazeLayout, cell: Coord, action: str) -> Coord:
        return apply_enemy_action(layout, cell, action)

    def resolve_player_action(self, layout: MazeLayout, cell: Coord, action: str) -> Coord:
        return resolve_player_action(layout, cell, action)

    def resolve_player_transition(self, layout: MazeLayout, cell: Coord, action: str):
        return resolve_player_transition(layout, cell, action)

    def initial_enemy_state(self, spec: EnemySpec) -> EnemyRuntimeState:
        behavior = self.behavior_for_spec(spec)
        return EnemyRuntimeState(
            activated=spec.wake_goal_distance < 0 and spec.spawn_delay_turns <= 0,
            turns_remaining=spec.lifetime_turns,
            turns_until_spawn=spec.spawn_delay_turns,
            behavior_state=behavior.initial_behavior_state(spec),
        )

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
            enemy = choose_greedy_step(
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
                role=enemy.role,
                movement_type=enemy.movement_type,
                move_priority=enemy.move_priority,
                step_count=enemy.step_count,
                facing_index=enemy.facing_index,
                traits=enemy.traits,
                wake_goal_distance=enemy.wake_goal_distance,
                lifetime_turns=enemy.lifetime_turns,
                spawn_delay_turns=enemy.spawn_delay_turns,
                respawn_delay_turns=enemy.respawn_delay_turns,
                spawn_cell=enemy.cell,
            )
            for enemy in enemy_spawns
        )
        enemy_positions = tuple(None if enemy.spawn_delay_turns > 0 else enemy.cell for enemy in enemy_spawns)
        next_enemy_locations, _, _ = self._step_enemy_positions(
            layout=layout,
            player_location=player_location,
            enemy_positions=enemy_positions,
            enemy_states=tuple(self.initial_enemy_state(spec) for spec in enemy_specs),
            enemy_specs=enemy_specs,
            goal_cells=(),
            zone_spawners=(),
            spawner_states=(),
            spawned_enemies=(),
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
        goal_cells: tuple[Coord, ...] = (),
        zone_spawners: tuple[ZoneSpawnerSpec, ...] = (),
    ) -> GameState | None:
        transition = self.resolve_player_transition(layout, state.player_position, action)
        enemy_states = state.enemy_states
        if len(enemy_states) != len(enemy_specs):
            enemy_states = tuple(self.initial_enemy_state(spec) for spec in enemy_specs)

        next_spawner_states, next_spawned_enemies = self._advance_spawner_states(
            zone_spawners=zone_spawners,
            spawner_states=state.spawner_states,
            player_location=transition.stepped_cell,
            occupied_cells={
                position
                for position in state.enemy_positions
                if position is not None
            } | {
                enemy.position
                for enemy in state.spawned_enemies
                if enemy.position is not None
            },
            spawned_enemies=list(state.spawned_enemies),
        )

        next_enemy_locations, next_enemy_states, next_spawned_enemies = self._step_enemy_positions(
            layout=layout,
            player_location=transition.stepped_cell,
            enemy_positions=state.enemy_positions,
            enemy_states=enemy_states,
            enemy_specs=enemy_specs,
            goal_cells=goal_cells,
            zone_spawners=zone_spawners,
            spawner_states=next_spawner_states,
            spawned_enemies=next_spawned_enemies,
        )
        if next_enemy_locations is None:
            return None

        turn_end_transition = resolve_player_turn_end_transition(layout, transition.resolved_cell)
        return GameState(
            player_position=turn_end_transition.resolved_cell,
            enemy_positions=next_enemy_locations,
            enemy_states=next_enemy_states,
            spawned_enemies=next_spawned_enemies,
            spawner_states=next_spawner_states,
        )

    def step_pathing_enemy(
        self,
        layout: MazeLayout,
        player_location: Coord,
        enemy_index: int,
        enemy_positions: list[Coord | None],
        enemy_states: list[EnemyRuntimeState],
        enemy_specs: tuple[EnemySpec, ...],
        choose_next_cell,
    ) -> bool:
        final_location: Coord | None = None
        spec = enemy_specs[enemy_index]
        for _ in range(spec.step_count):
            current_location = enemy_positions[enemy_index]
            if current_location is None:
                break

            blocked_cells = self.blocked_cells_for_mover(enemy_index, enemy_positions, enemy_specs)
            next_enemy_location = choose_next_cell(current_location, blocked_cells)
            if next_enemy_location == current_location:
                continue

            caught_player = self.move_enemy_to_target(
                player_location=player_location,
                enemy_index=enemy_index,
                enemy_positions=enemy_positions,
                enemy_specs=enemy_specs,
                enemy_states=enemy_states,
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

        resolved_cell, used_teleport = self.resolve_turn_end_enemy_transition(layout, final_location)
        if not used_teleport:
            return False

        return self.move_enemy_to_target(
            player_location=player_location,
            enemy_index=enemy_index,
            enemy_positions=enemy_positions,
            enemy_states=enemy_states,
            enemy_specs=enemy_specs,
            next_enemy_location=resolved_cell,
        )

    def move_enemy_to_target(
        self,
        player_location: Coord,
        enemy_index: int,
        enemy_positions: list[Coord | None],
        enemy_states: list[EnemyRuntimeState],
        enemy_specs: tuple[EnemySpec, ...],
        next_enemy_location: Coord,
    ) -> bool:
        current_location = enemy_positions[enemy_index]
        if current_location is None or next_enemy_location == current_location:
            return False

        target_index = enemy_index_at_position(enemy_positions, next_enemy_location, enemy_index)
        if target_index is not None:
            contact_result = resolve_enemy_contact(enemy_index, target_index, enemy_specs)
            if contact_result == CONTACT_BLOCKED:
                return False

            enemy_positions[enemy_index] = next_enemy_location
            if contact_result == CONTACT_TARGET_DIES:
                enemy_positions[target_index] = None
                enemy_states[target_index] = self.build_despawned_state(enemy_specs[target_index])
            elif contact_result == CONTACT_MOVER_DIES:
                enemy_positions[enemy_index] = None
                enemy_states[enemy_index] = self.build_despawned_state(enemy_specs[enemy_index])
            return False

        enemy_positions[enemy_index] = next_enemy_location
        return next_enemy_location == player_location

    def build_despawned_state(self, spec: EnemySpec) -> EnemyRuntimeState:
        if spec.respawn_delay_turns <= 0:
            return EnemyRuntimeState()
        behavior = self.behavior_for_spec(spec)
        return EnemyRuntimeState(
            activated=False,
            turns_remaining=spec.lifetime_turns,
            turns_until_spawn=spec.respawn_delay_turns,
            behavior_state=behavior.initial_behavior_state(spec),
        )

    def behavior_for_spec(self, spec: EnemySpec) -> EnemyBehavior:
        movement_type = resolved_movement_type(spec.enemy_type, role=spec.role, explicit_movement_type=spec.movement_type)
        return self.behavior_registry.get(movement_type, self.behavior_registry["greedy"])

    def blocked_cells_for_mover(self, mover_index, enemy_positions, enemy_specs):
        return blocked_cells_for_mover(mover_index, enemy_positions, enemy_specs)

    def resolve_turn_end_enemy_transition(self, layout: MazeLayout, final_location: Coord) -> tuple[Coord, bool]:
        transition = resolve_enemy_turn_end_transition(layout, final_location)
        return transition.resolved_cell, transition.used_teleport

    def _step_enemy_positions(
        self,
        layout: MazeLayout,
        player_location: Coord,
        enemy_positions: tuple[Coord | None, ...],
        enemy_states: tuple[EnemyRuntimeState, ...],
        enemy_specs: tuple[EnemySpec, ...],
        goal_cells: tuple[Coord, ...],
        zone_spawners: tuple[ZoneSpawnerSpec, ...],
        spawner_states,
        spawned_enemies: tuple[SpawnedEnemyState, ...],
    ) -> tuple[tuple[Coord | None, ...] | None, tuple[EnemyRuntimeState, ...], tuple[SpawnedEnemyState, ...]]:
        combined_enemy_positions = list(enemy_positions) + [enemy.position for enemy in spawned_enemies]
        combined_enemy_states = list(enemy_states) + [enemy.runtime_state for enemy in spawned_enemies]
        combined_enemy_specs = enemy_specs + tuple(enemy.spec for enemy in spawned_enemies)

        for enemy_index, enemy_location in enumerate(combined_enemy_positions):
            spec = combined_enemy_specs[enemy_index]
            behavior = self.behavior_for_spec(spec)
            state = combined_enemy_states[enemy_index]
            if enemy_location is None:
                spawned_location, spawned_state = advance_spawn_state(
                    behavior=behavior,
                    spec=spec,
                    state=state,
                    player_location=player_location,
                    enemy_positions=combined_enemy_positions,
                )
                combined_enemy_positions[enemy_index] = spawned_location
                combined_enemy_states[enemy_index] = spawned_state
                continue

            activated_state = update_activation_state(spec, state, player_location, goal_cells)
            combined_enemy_states[enemy_index] = activated_state
            if not activated_state.activated:
                continue

            step_result = behavior.step_enemy(
                engine=self,
                layout=layout,
                player_location=player_location,
                enemy_index=enemy_index,
                enemy_positions=combined_enemy_positions,
                enemy_states=combined_enemy_states,
                enemy_specs=combined_enemy_specs,
                spec=spec,
            )
            if step_result.caught_player:
                combined_enemy_states[enemy_index] = step_result.next_state
                return None, tuple(enemy_states), spawned_enemies
            combined_enemy_states[enemy_index] = advance_lifetime(spec, step_result.next_state, combined_enemy_positions, enemy_index)

        if any(enemy_location == player_location for enemy_location in combined_enemy_positions if enemy_location is not None):
            return None, tuple(enemy_states), spawned_enemies

        base_count = len(enemy_positions)
        next_spawned = tuple(
            replace(
                spawned_enemies[index],
                position=combined_enemy_positions[base_count + index],
                runtime_state=combined_enemy_states[base_count + index],
            )
            for index in range(len(spawned_enemies))
            if combined_enemy_positions[base_count + index] is not None
        )
        return tuple(combined_enemy_positions[:base_count]), tuple(combined_enemy_states[:base_count]), next_spawned

    def _advance_spawner_states(
        self,
        zone_spawners: tuple[ZoneSpawnerSpec, ...],
        spawner_states,
        player_location: Coord,
        occupied_cells: set[Coord],
        spawned_enemies: list[SpawnedEnemyState],
    ) -> tuple[tuple, tuple[SpawnedEnemyState, ...]]:
        if not zone_spawners:
            return spawner_states, tuple(spawned_enemies)
        next_states = list(spawner_states)
        for index, spawner in enumerate(zone_spawners):
            behavior = self.behavior_for_spec(spawner.enemy_spec)
            next_state, spawned_enemy = advance_zone_spawner(
                spawner=spawner,
                state=spawner_states[index],
                behavior=behavior,
                player_location=player_location,
                occupied_cells=occupied_cells,
            )
            next_states[index] = next_state
            if spawned_enemy is not None:
                spawned_enemies.append(spawned_enemy)
                if spawned_enemy.position is not None:
                    occupied_cells.add(spawned_enemy.position)
        return tuple(next_states), tuple(spawned_enemies)
