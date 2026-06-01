# AGENTS.md

This file gives repo-local guidance for agents working in this project.

## Parent Guidance

This repo also sits under a parent project guide:

- `C:\Users\echri\godotFolder\Godot_v4.5.1-stable_mono_win64\godot_v4.5.1_projects\Pharohs_Tomb\AGENTS.md`

Treat that parent file as inherited guidance for Godot 4.5, GDScript-only work, turn-based gameplay boundaries, and project-scope guardrails. If this repo-local file and the parent file diverge, follow the stricter rule unless the user explicitly redirects the work.

## Architectural Priorities

- Preserve the shared Python/Godot schema bridge.
- Prefer canonical fields and `ecs_components` over direct legacy `role` branching in new runtime code.
- Treat the current Godot runtime architecture as:
  `record -> registry -> system -> view`
- Keep scene scripts thin. New behavior logic should usually live in systems, not per-scene controllers.

## Important Runtime Areas

Enemy runtime:

- `EnemyManager/enemy_runtime_record.gd`
- `EnemyManager/enemy_runtime_registry.gd`
- `EnemyManager/enemy_turn_system.gd`
- `EnemyManager/enemy_contact_system.gd`
- `EnemyManager/enemy_behavior_systems.gd`
- `EnemyManager/enemy_lifecycle_system.gd`

Zone spawner runtime:

- `EnemyManager/zone_spawner_runtime_record.gd`
- `EnemyManager/zone_spawner_runtime_registry.gd`
- `EnemyManager/zone_spawner_system.gd`
- `EnemyManager/zone_spawn_controller.gd`

Board interaction runtime:

- `MazeGenerator/board_interaction_system.gd`
- `MazeGenerator/maze_data.gd`

Shared schema:

- `Resources/DataSchemas/enemy_ecs_schema.json`
- `Global/enemy_schema_bridge.gd`
- `Tools/minotaur_export/shared_enemy_schema.py`

## Working Rules

- Do not remove legacy compatibility fields lightly. `role`, `movement_type`, and `traits` are still part of the long bridge.
- When adding a new actor/runtime feature, prefer:
  canonical payload -> runtime record -> registry -> system -> presentation
- Avoid reintroducing node-only authority for gameplay state during turn resolution.
- Keep Python solver/runtime behavior aligned with Godot runtime behavior when changing movement, teleport, spawner, or contact rules.

## Docs To Keep In Sync

- `README.md`
- `Design_Docs/ECS_Component_Migration_Plan.md`
- `Design_Docs/ECS_Bridge_Runtime_Validation_Guide.md`
- `Design_Docs/Runtime_Architecture.md`
- `Resources/Worlds/SolverTestMazes/README.md`

Useful parent references:

- `..\Godot_Instruction_Manual\index.md`
- `..\skills\pharaohs-tomb-project-safety\SKILL.md`
- `..\skills\godot-architecture-turn-based-2d\SKILL.md`

## Validation

Before closeout, prefer running:

```powershell
python -m unittest Tools.tests.test_minotaur_export
& 'C:\Users\echri\godotFolder\Godot_v4.5.1-stable_mono_win64\Godot_v4.5.1-stable_mono_win64_console.exe' --headless --path . --quit-after 1
```

If a change affects runtime agreement, also consider the ECS bridge validation probes under:

- `Resources/Worlds/SolverTestMazes/Probes/ECSBridge`
