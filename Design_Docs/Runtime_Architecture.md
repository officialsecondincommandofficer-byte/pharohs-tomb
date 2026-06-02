# Runtime Architecture

This document describes the runtime architecture that now backs the current gameplay slice in both the Python solver/export path and the Godot runtime.

## Core Shape

The runtime is intentionally moving toward:

- canonical payloads
- runtime records
- registries
- systems
- presentation views

Short version:

- payloads describe authored intent
- records hold authoritative runtime state
- registries group records
- systems evolve state
- views render and animate state

## Shared Contract

Enemy data is normalized through:

- `Resources/DataSchemas/enemy_ecs_schema.json`
- `Tools/minotaur_export/shared_enemy_schema.py`
- `Global/enemy_schema_bridge.gd`

This bridge still accepts legacy `role`, `movement_type`, and `traits`, but new runtime logic should prefer canonical fields and `ecs_components`.

## Godot Runtime Shape

### Enemies

Primary files:

- `EnemyManager/enemy_runtime_record.gd`
- `EnemyManager/enemy_runtime_registry.gd`
- `EnemyManager/enemy_turn_system.gd`
- `EnemyManager/enemy_contact_system.gd`
- `EnemyManager/enemy_behavior_systems.gd`
- `EnemyManager/enemy_lifecycle_system.gd`

Pattern:

- `EnemyRuntimeRecord` is the authoritative per-enemy runtime snapshot
- `EnemyRuntimeRegistry` stores the active enemy records
- turn/contact/behavior/lifecycle systems mutate record state
- enemy scene scripts mainly hydrate, preview, animate, and render

### Zone Spawners

Primary files:

- `EnemyManager/zone_spawner_runtime_record.gd`
- `EnemyManager/zone_spawner_runtime_registry.gd`
- `EnemyManager/zone_spawner_system.gd`
- `EnemyManager/zone_spawn_controller.gd`

Pattern:

- spawner countdown/config state lives in runtime records
- the controller coordinates, but the runtime system performs warning and spawn resolution

### Board Interactions

Primary files:

- `MazeGenerator/board_interaction_system.gd`
- `MazeGenerator/maze_data.gd`

Pattern:

- `MazeData` owns board state and lookups
- `BoardInteractionSystem` owns runtime movement legality and transition rules
- teleports, actor-specific walls, and turn-end transitions should go through the system layer

### World Runtime Core

Primary files:

- `GameManager/world_runtime_registry.gd`
- `GameManager/world_runtime_state.gd`
- `GameManager/world_enemy_phase_runtime_payload.gd`
- `GameManager/world_board_effect_runtime_payload.gd`
- `GameManager/world_turn_system.gd`
- `Player/player_runtime_state.gd`
- `GameManager/game_manager.gd`

Pattern:

- `WorldRuntimeRegistry` owns the active canonical runtime snapshot plus start/history snapshots
- `WorldRuntimeState` is the mutable world snapshot shape stored inside the registry
- enemy/spawner world-state data now lives in typed runtime payload adapters instead of raw registry dictionaries
- board-effect runtime state has an explicit typed payload even though current mutable effect state is intentionally minimal
- player runtime state now lives in the world runtime instead of only on the player node
- `WorldTurnSystem` resolves player step, enemy phase, spawner phase, turn-end transitions, and win/loss sequencing
- `GameManager` still owns session flow, but it should delegate turn mutation, reset, undo, and replay through the world registry layer
- the `Player` node is now primarily input plus presentation, not the only gameplay truth

## Python Runtime Shape

The Python side is still not an ECS engine, but it follows the same architectural direction:

- canonical schema bridge feeds exported payloads
- rule modules consume component data first
- enemy and spawner runtime state is explicit in solver models
- movement and turn-end transition rules are centralized

Representative files:

- `Tools/minotaur_export/models.py`
- `Tools/minotaur_export/enemy_turn_rules.py`
- `Tools/minotaur_export/zone_spawner_rules.py`
- `Tools/minotaur_export/movement.py`

## Design Rules

When adding new gameplay runtime behavior, prefer these rules:

1. Put authored intent in canonical payloads first.
2. Put mutable runtime state in a record, not only on a scene node.
3. Put orchestration and decision logic in a system.
4. Keep scene scripts thin and presentation-focused.
5. Preserve legacy compatibility at load boundaries until old payloads are intentionally retired.

## Anti-Patterns To Avoid

- new scene-local behavior trees for enemy families
- reading `role` directly in new runtime logic when `ecs_components` already carries the same intent
- using nodes as the only authoritative state source during turn resolution
- adding one-off controller arrays for spawned actor state instead of a record/registry shape

## Next Expansion Areas

The current runtime architecture is strong for enemies, spawners, and board interaction transitions. Future work should apply the same shape to:

- additional spawned actor families
- richer hazard or board-effect runtime state
- broader actor participation in the world registry when future actor families need mutable runtime state
