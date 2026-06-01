from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "Resources" / "DataSchemas" / "enemy_ecs_schema.json"


@lru_cache(maxsize=1)
def load_enemy_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def resolved_enemy_type(enemy_type: str) -> str:
    schema = load_enemy_schema()
    profile = schema.get("enemy_type_profiles", {}).get(enemy_type, {})
    return str(profile.get("canonical_enemy_type", enemy_type))


def resolved_enemy_role(
    enemy_type: str,
    move_priority: str = "horizontal",
    traits: tuple[str, ...] = (),
    explicit_role: str = "",
) -> str:
    if explicit_role:
        return explicit_role
    if "escape_linked" in traits:
        return "linked_escape_hunter"
    schema = load_enemy_schema()
    profile = schema.get("enemy_type_profiles", {}).get(enemy_type, {})
    default_roles = profile.get("default_role_by_move_priority", {})
    if move_priority in default_roles:
        return str(default_roles[move_priority])
    return str(profile.get("default_role", enemy_type))


def resolved_movement_type(
    enemy_type: str,
    role: str = "",
    explicit_movement_type: str = "",
) -> str:
    if explicit_movement_type:
        return explicit_movement_type
    schema = load_enemy_schema()
    resolved_role_name = role or resolved_enemy_role(enemy_type)
    role_profile = schema.get("role_profiles", {}).get(resolved_role_name, {})
    if role_profile:
        return str(role_profile.get("movement_type", "greedy"))
    return "greedy"


def build_enemy_bridge_payload(
    *,
    enemy_type: str,
    move_priority: str = "horizontal",
    role: str = "",
    movement_type: str = "",
    traits: tuple[str, ...] = (),
    step_count: int = 1,
    facing_index: int = 2,
    wake_goal_distance: int = -1,
    lifetime_turns: int = -1,
    spawn_delay_turns: int = 0,
    respawn_delay_turns: int = 0,
    patrol_route: tuple[tuple[int, int], ...] = (),
    patrol_mode: str = "ping_pong",
    behavior_seed: int = 0,
) -> dict[str, Any]:
    schema = load_enemy_schema()
    canonical_enemy_type = resolved_enemy_type(enemy_type)
    resolved_role_name = resolved_enemy_role(
        enemy_type,
        move_priority=move_priority,
        traits=traits,
        explicit_role=role,
    )
    resolved_movement_name = resolved_movement_type(
        enemy_type,
        role=resolved_role_name,
        explicit_movement_type=movement_type,
    )
    role_profile = copy.deepcopy(schema.get("role_profiles", {}).get(resolved_role_name, {}))
    enemy_type_profile = schema.get("enemy_type_profiles", {}).get(enemy_type, {})
    components = copy.deepcopy(role_profile.get("components", {}))
    components.setdefault("identity", {})
    components["identity"]["canonical_enemy_type"] = canonical_enemy_type
    components["identity"]["scene_family"] = str(
        enemy_type_profile.get("scene_family", role_profile.get("scene_family", schema.get("default_scene_family", "chaser")))
    )
    components.setdefault("movement", {})
    components["movement"]["family"] = resolved_movement_name
    components["movement"]["step_count"] = step_count
    components["movement"]["move_priority"] = move_priority
    components["movement"]["facing_index"] = facing_index
    components["activation"] = {
        "wake_goal_distance": wake_goal_distance,
        "spawn_delay_turns": spawn_delay_turns,
        "respawn_delay_turns": respawn_delay_turns,
    }
    components["lifecycle"] = {
        "lifetime_turns": lifetime_turns,
    }
    if patrol_route:
        components["movement"]["patrol_route"] = [list(cell) for cell in patrol_route]
        components["movement"]["patrol_mode"] = patrol_mode
    if behavior_seed != 0:
        components.setdefault("behavior", {})
        components["behavior"]["seed"] = behavior_seed

    trait_components = schema.get("trait_components", {})
    for trait in traits:
        trait_payload = copy.deepcopy(trait_components.get(trait, {}))
        for component_name, component_values in trait_payload.items():
            components.setdefault(component_name, {})
            components[component_name].update(component_values)

    return {
        "schema_version": int(schema.get("schema_version", 1)),
        "canonical_enemy_type": canonical_enemy_type,
        "archetype_id": str(role_profile.get("archetype_id", f"enemy.{resolved_role_name}")),
        "scene_family": components["identity"]["scene_family"],
        "legacy": {
            "enemy_type": enemy_type,
            "role": resolved_role_name,
            "movement_type": resolved_movement_name,
            "traits": list(traits),
        },
        "components": components,
    }
