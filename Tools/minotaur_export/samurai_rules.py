from __future__ import annotations

from dataclasses import replace

from .enemy_behavior import EnemyBehavior, EnemyStepResult
from .models import Coord, EnemyRuntimeState, EnemySpec, SamuraiBehaviorState

SAMURAI_ROTATIONS: tuple[Coord, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))
SAMURAI_CHARGE_DELAYS: tuple[int, ...] = (3, 2, 1)


class SamuraiBehavior(EnemyBehavior):
    def initial_behavior_state(self, spec: EnemySpec) -> SamuraiBehaviorState:
        return SamuraiBehaviorState(facing_index=spec.facing_index)

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
        del layout, spec
        current_location = enemy_positions[enemy_index]
        if current_location is None:
            return EnemyStepResult(caught_player=False, next_state=enemy_states[enemy_index])

        behavior_state = enemy_states[enemy_index].behavior_state
        if not isinstance(behavior_state, SamuraiBehaviorState):
            behavior_state = SamuraiBehaviorState()

        if behavior_state.attack_phase == -1:
            rotated_facing = (behavior_state.facing_index + 1) % len(SAMURAI_ROTATIONS)
            next_behavior_state = SamuraiBehaviorState(facing_index=rotated_facing)
            if _samurai_can_see_player(current_location, player_location, rotated_facing):
                next_behavior_state = SamuraiBehaviorState(
                    facing_index=rotated_facing,
                    attack_phase=0,
                    turns_until_dash=SAMURAI_CHARGE_DELAYS[0],
                )
            next_state = replace(enemy_states[enemy_index], behavior_state=next_behavior_state)
            enemy_states[enemy_index] = next_state
            return EnemyStepResult(caught_player=False, next_state=next_state)

        turns_until_dash = behavior_state.turns_until_dash - 1
        if turns_until_dash > 0:
            next_state = replace(
                enemy_states[enemy_index],
                behavior_state=SamuraiBehaviorState(
                    facing_index=behavior_state.facing_index,
                    attack_phase=behavior_state.attack_phase,
                    turns_until_dash=turns_until_dash,
                ),
            )
            enemy_states[enemy_index] = next_state
            return EnemyStepResult(caught_player=False, next_state=next_state)

        blocked_cells = engine.blocked_cells_for_mover(enemy_index, enemy_positions, enemy_specs)
        next_enemy_location = _choose_samurai_dash_target(
            player_location=player_location,
            enemy_location=current_location,
            facing_index=behavior_state.facing_index,
            blocked_cells=blocked_cells,
        )
        next_state = replace(enemy_states[enemy_index], behavior_state=_advance_samurai_state(behavior_state))
        enemy_states[enemy_index] = next_state
        if next_enemy_location == current_location:
            return EnemyStepResult(caught_player=False, next_state=next_state)

        caught_player = engine.move_enemy_to_target(
            player_location=player_location,
            enemy_index=enemy_index,
            enemy_positions=enemy_positions,
            enemy_states=enemy_states,
            enemy_specs=enemy_specs,
            next_enemy_location=next_enemy_location,
        )
        if caught_player:
            return EnemyStepResult(caught_player=True, next_state=next_state)

        current_location = enemy_positions[enemy_index]
        if current_location is None:
            return EnemyStepResult(caught_player=False, next_state=next_state)

        resolved_cell, used_teleport = engine.resolve_turn_end_enemy_transition(layout, current_location)
        if not used_teleport:
            return EnemyStepResult(caught_player=False, next_state=next_state)

        caught_player = engine.move_enemy_to_target(
            player_location=player_location,
            enemy_index=enemy_index,
            enemy_positions=enemy_positions,
            enemy_states=enemy_states,
            enemy_specs=enemy_specs,
            next_enemy_location=resolved_cell,
        )
        return EnemyStepResult(caught_player=caught_player, next_state=next_state)


def _samurai_can_see_player(enemy_location: Coord, player_location: Coord, facing_index: int) -> bool:
    delta_x = player_location[0] - enemy_location[0]
    delta_y = player_location[1] - enemy_location[1]
    facing_x, facing_y = SAMURAI_ROTATIONS[facing_index]

    if facing_x != 0:
        return delta_y == 0 and delta_x != 0 and (1 if delta_x > 0 else -1) == facing_x
    return delta_x == 0 and delta_y != 0 and (1 if delta_y > 0 else -1) == facing_y


def _choose_samurai_dash_target(
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


def _advance_samurai_state(state: SamuraiBehaviorState) -> SamuraiBehaviorState:
    next_phase = state.attack_phase + 1
    if next_phase >= len(SAMURAI_CHARGE_DELAYS):
        return SamuraiBehaviorState(facing_index=state.facing_index)
    return SamuraiBehaviorState(
        facing_index=state.facing_index,
        attack_phase=next_phase,
        turns_until_dash=SAMURAI_CHARGE_DELAYS[next_phase],
    )
