from __future__ import annotations

from dataclasses import replace

from .enemy_behavior import EnemyBehavior, EnemyStepResult
from .models import Coord, EnemyRuntimeState, EnemySpec, WandererBehaviorState


WANDERER_DIRECTIONS: tuple[Coord, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))


def choose_wanderer_step(
    layout,
    enemy_location: Coord,
    blocked_cells: set[Coord],
    facing_index: int,
    behavior_seed: int,
    decision_count: int,
    visited_ticks: tuple[tuple[Coord, int], ...],
) -> tuple[Coord, int]:
    facing = facing_index % len(WANDERER_DIRECTIONS)
    preferred = [facing, (facing - 1) % 4, (facing + 1) % 4]
    back = (facing + 2) % 4

    visit_lookup = dict(visited_ticks)
    preferred_legal = [candidate for candidate in preferred if _can_move(layout, enemy_location, blocked_cells, candidate)]
    if preferred_legal:
        chosen_direction = _choose_oldest_visit_direction(
            candidate_directions=preferred_legal,
            enemy_location=enemy_location,
            behavior_seed=behavior_seed,
            decision_count=decision_count,
            visit_lookup=visit_lookup,
        )
        return _apply_direction(enemy_location, chosen_direction), chosen_direction

    if _can_move(layout, enemy_location, blocked_cells, back):
        return _apply_direction(enemy_location, back), back

    return enemy_location, facing


def _choose_oldest_visit_direction(
    candidate_directions: list[int],
    enemy_location: Coord,
    behavior_seed: int,
    decision_count: int,
    visit_lookup: dict[Coord, int],
) -> int:
    oldest_visit_tick = min(visit_lookup.get(_apply_direction(enemy_location, direction_index), -1) for direction_index in candidate_directions)
    oldest_candidates = [
        direction_index
        for direction_index in candidate_directions
        if visit_lookup.get(_apply_direction(enemy_location, direction_index), -1) == oldest_visit_tick
    ]
    choice_index = _seeded_choice_index(
        behavior_seed=behavior_seed,
        decision_count=decision_count,
        enemy_location=enemy_location,
        option_count=len(oldest_candidates),
    )
    return oldest_candidates[choice_index]


def _seeded_choice_index(
    behavior_seed: int,
    decision_count: int,
    enemy_location: Coord,
    option_count: int,
) -> int:
    mixed = (
        behavior_seed * 1103515245
        + decision_count * 12345
        + enemy_location[0] * 92821
        + enemy_location[1] * 68917
    ) & 0x7FFFFFFF
    return mixed % option_count


def _can_move(layout, enemy_location: Coord, blocked_cells: set[Coord], direction_index: int) -> bool:
    candidate = _apply_direction(enemy_location, direction_index)
    if not layout.contains(candidate):
        return False
    if candidate in blocked_cells:
        return False
    return not layout.is_enemy_blocked(enemy_location, candidate)


def _apply_direction(enemy_location: Coord, direction_index: int) -> Coord:
    dx, dy = WANDERER_DIRECTIONS[direction_index]
    return (enemy_location[0] + dx, enemy_location[1] + dy)


class WandererBehavior(EnemyBehavior):
    def initial_behavior_state(self, spec: EnemySpec) -> WandererBehaviorState:
        return WandererBehaviorState(
            facing_index=spec.component_int("movement", "facing_index", spec.facing_index) % len(WANDERER_DIRECTIONS)
        )

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

        behavior_state = enemy_states[enemy_index].behavior_state
        if not isinstance(behavior_state, WandererBehaviorState):
            behavior_state = self.initial_behavior_state(spec)

        blocked_cells = engine.blocked_cells_for_mover(enemy_index, enemy_positions, enemy_specs)
        next_enemy_location, next_facing = choose_wanderer_step(
            layout=layout,
            enemy_location=current_location,
            blocked_cells=blocked_cells,
            facing_index=behavior_state.facing_index,
            behavior_seed=spec.component_int("behavior", "seed", spec.behavior_seed),
            decision_count=behavior_state.decision_count,
            visited_ticks=behavior_state.visited_ticks,
        )

        next_visit_tick = behavior_state.visit_tick + 1
        visited_lookup = dict(behavior_state.visited_ticks)
        if next_enemy_location != current_location:
            visited_lookup[next_enemy_location] = next_visit_tick
        next_state = replace(
            enemy_states[enemy_index],
            behavior_state=WandererBehaviorState(
                facing_index=next_facing,
                decision_count=behavior_state.decision_count + 1,
                visit_tick=next_visit_tick,
                visited_ticks=tuple(sorted(visited_lookup.items())),
            ),
        )
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
