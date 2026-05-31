from __future__ import annotations

from dataclasses import replace

from .enemy_behavior import EnemyBehavior, EnemyStepResult
from .models import Coord, EnemyRuntimeState, EnemySpec, PatrollerBehaviorState


PATROL_MODE_LOOP = "loop"
PATROL_MODE_PING_PONG = "ping_pong"


def _can_step(layout, current_location: Coord, next_location: Coord, blocked_cells: set[Coord]) -> bool:
    if next_location in blocked_cells:
        return False
    if not layout.contains(next_location):
        return False
    if abs(next_location[0] - current_location[0]) + abs(next_location[1] - current_location[1]) != 1:
        return False
    return not layout.is_enemy_blocked(current_location, next_location)


class PatrollerBehavior(EnemyBehavior):
    def initial_behavior_state(self, spec: EnemySpec) -> PatrollerBehaviorState:
        del spec
        return PatrollerBehaviorState()

    def choose_spawn_cell(
        self,
        spec: EnemySpec,
        player_location: Coord,
        occupied_cells: set[Coord],
    ) -> Coord | None:
        del player_location
        if spec.spawn_cell is None or spec.spawn_cell in occupied_cells:
            return None
        return spec.spawn_cell

    def step_enemy(
        self,
        engine,
        layout,
        player_location: Coord,
        enemy_index: int,
        enemy_positions: list[Coord | None],
        enemy_states: list[EnemyRuntimeState],
        enemy_specs: tuple[EnemySpec, ...],
        spec: EnemySpec,
    ) -> EnemyStepResult:
        current_location = enemy_positions[enemy_index]
        if current_location is None:
            return EnemyStepResult(caught_player=False, next_state=enemy_states[enemy_index])

        route = spec.patrol_route or (current_location,)
        behavior_state = enemy_states[enemy_index].behavior_state
        if not isinstance(behavior_state, PatrollerBehaviorState):
            behavior_state = PatrollerBehaviorState()

        if len(route) <= 1:
            next_state = replace(enemy_states[enemy_index], behavior_state=behavior_state)
            enemy_states[enemy_index] = next_state
            return EnemyStepResult(caught_player=False, next_state=next_state)

        patrol_index = max(0, min(behavior_state.patrol_index, len(route) - 1))
        patrol_direction = 1 if behavior_state.patrol_direction >= 0 else -1
        patrol_mode = spec.patrol_mode if spec.patrol_mode in (PATROL_MODE_LOOP, PATROL_MODE_PING_PONG) else PATROL_MODE_PING_PONG
        next_index = _next_patrol_index(patrol_index, patrol_direction, len(route), patrol_mode)
        next_direction = patrol_direction if patrol_mode == PATROL_MODE_LOOP else _next_patrol_direction(patrol_index, patrol_direction, len(route))

        target_cell = route[next_index]
        blocked_cells = engine.blocked_cells_for_mover(enemy_index, enemy_positions, enemy_specs)
        if not _can_step(layout, current_location, target_cell, blocked_cells):
            if patrol_mode == PATROL_MODE_LOOP:
                next_state = replace(
                    enemy_states[enemy_index],
                    behavior_state=PatrollerBehaviorState(
                        patrol_index=patrol_index,
                        patrol_direction=patrol_direction,
                    ),
                )
                enemy_states[enemy_index] = next_state
                return EnemyStepResult(caught_player=False, next_state=next_state)

            patrol_direction *= -1
            next_direction = patrol_direction
            next_index = patrol_index + patrol_direction
            if next_index < 0 or next_index >= len(route):
                next_state = replace(
                    enemy_states[enemy_index],
                    behavior_state=PatrollerBehaviorState(
                        patrol_index=patrol_index,
                        patrol_direction=patrol_direction,
                    ),
                )
                enemy_states[enemy_index] = next_state
                return EnemyStepResult(caught_player=False, next_state=next_state)
            target_cell = route[next_index]
            if not _can_step(layout, current_location, target_cell, blocked_cells):
                next_state = replace(
                    enemy_states[enemy_index],
                    behavior_state=PatrollerBehaviorState(
                        patrol_index=patrol_index,
                        patrol_direction=patrol_direction,
                    ),
                )
                enemy_states[enemy_index] = next_state
                return EnemyStepResult(caught_player=False, next_state=next_state)

        next_state = replace(
            enemy_states[enemy_index],
            behavior_state=PatrollerBehaviorState(
                patrol_index=next_index,
                patrol_direction=next_direction,
            ),
        )
        enemy_states[enemy_index] = next_state
        caught_player = engine.move_enemy_to_target(
            player_location=player_location,
            enemy_index=enemy_index,
            enemy_positions=enemy_positions,
            enemy_states=enemy_states,
            enemy_specs=enemy_specs,
            next_enemy_location=target_cell,
        )
        return EnemyStepResult(caught_player=caught_player, next_state=next_state)


def _next_patrol_index(patrol_index: int, patrol_direction: int, route_length: int, patrol_mode: str) -> int:
    if patrol_mode == PATROL_MODE_LOOP:
        return (patrol_index + 1) % route_length
    next_index = patrol_index + patrol_direction
    if next_index < 0 or next_index >= route_length:
        return patrol_index - patrol_direction
    return next_index


def _next_patrol_direction(patrol_index: int, patrol_direction: int, route_length: int) -> int:
    next_index = patrol_index + patrol_direction
    if next_index < 0 or next_index >= route_length:
        return -patrol_direction
    return patrol_direction
