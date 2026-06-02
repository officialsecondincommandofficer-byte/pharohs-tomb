# ECS / Component Migration Plan

This document defines the long-bridge migration path from the current role-and-scene enemy model to a project-wide ECS/component model shared by Python and Godot.

## Goal

Adopt one canonical schema that both runtimes consume while preserving current authored data and shipped behaviors.

- Canonical source of truth: [enemy_ecs_schema.json](/C:/Users/echri/godotFolder/Godot_v4.5.1-stable_mono_win64/godot_v4.5.1_projects/Pharohs_Tomb/pharohs-tomb/Resources/DataSchemas/enemy_ecs_schema.json)
- Bridge principle: continue accepting `role`, `movement_type`, and `traits` until every caller has moved to component reads.
- Current split:
  Python is already system-leaning through rule modules.
  Godot is still mostly scene-selected and role-driven.

## Current Status

The migration is no longer just planned; most of the runtime bridge is now in place for the current gameplay slice.

Implemented today:

- clear app-shell vs gameplay-screen scene separation through `App/AppShell.tscn` and `Gameplay/GameplayScreen.tscn`
- shared enemy schema consumed by Python and Godot
- canonical enemy payload stamping during export and board load
- component-first solver/runtime behavior selection in Python
- Godot enemy runtime records, registries, and systems
- Godot zone spawner runtime records, registries, and systems
- Godot board interaction system for teleports, actor-specific walls, and turn-end transitions
- Godot world runtime registry for player state, undo/reset snapshots, replay history, and canonical turn resolution
- typed world-runtime payload adapters for enemy/spawner state and future mutable board effects
- scene scripts reduced to mostly presentation, hydration, and preview responsibilities

For the enemy-plus-spawner-plus-board-interaction slice, the runtime loop is effectively ECS-shaped already. The remaining project-wide work is mostly extending the same pattern to future actor types and keeping legacy compatibility intact while older payloads still exist.

## Canonical Model

Enemy data now resolves through a shared schema into:

- `canonical_enemy_type`: runtime family such as `greedy_chaser`, `samurai`, or `patroller`
- `canonical_archetype`: stable archetype id such as `enemy.greedy_chaser.horizontal`
- `ecs_schema_version`: schema version for compatibility checks
- `ecs_components`: normalized component payload

The component payload is intentionally bridge-shaped, not final-form ECS purity. It captures the stable seams we already use:

- `identity`
- `movement`
- `activation`
- `lifecycle`
- `contact`
- `spawn_context`
- `behavior`

## Migration Stages

### Stage 0: Shared Schema Bridge

Implemented in this branch.

- Python loads the shared schema through `Tools/minotaur_export/shared_enemy_schema.py`.
- Godot loads the same schema through `Global/enemy_schema_bridge.gd`.
- Enemy spawn normalization now stamps canonical fields onto runtime dictionaries.
- Exported `.tres` enemy dictionaries now carry `canonical_archetype` and `ecs_schema_version`.
- JSON manifests now include full `ecs_components` payloads for debugging, validation, and future tooling.

### Stage 1: Read Components First

Implemented for the current enemy runtime and solver paths.

- Python systems should prefer `bridge_payload["components"]` over hardcoded role checks.
- Godot enemy scenes should prefer `ecs_components.movement.family` and related component values over `role`.
- `EnemyManager` scene selection should remain bridged until scene families collapse into component-driven runners.

### Stage 2: Replace Role-Specific Scene Logic

Implemented for the current enemy families.

- Introduce component runners or system nodes for movement, activation, contact, and lifetime.
- Keep presentation scenes thin: sprite, animation hooks, and view sync only.
- Treat current `Chaser`, `Samurai`, `Patroller`, `StationaryBlocker`, `Minotaur`, and `Wanderer` scenes as presentation shells around systems.

### Stage 3: Project-Wide ECS Adoption

- Expand the shared schema pattern beyond enemies to player state, items, hazards, exits, teleports, and spawners.
- Move authored board payloads toward canonical component documents first, legacy aliases second.
- Remove compatibility aliases only after save/load, export, runtime, and tests no longer depend on them.

Current priority inside Stage 3:

- keep board interaction rules centralized in shared runtime systems
- keep player state and turn snapshots flowing through the world runtime registry instead of node-only state
- use runtime records and registries for any new spawned actor families
- avoid reintroducing scene-local behavior logic for new Godot actor types

## Compatibility Rules

During the bridge, these rules are mandatory:

- New code may write canonical fields in addition to legacy fields.
- Loaders must tolerate payloads that only contain legacy fields.
- Runtime behavior changes must be driven by components only when they are proven equivalent to the legacy path.
- Removing `role`, `movement_type`, or `traits` from authored resources is out of scope until later stages.

## Why This Shape

This plan picks the enemy spawn dictionary as the migration seam because it already crosses all the boundaries we care about:

- Python generator/exporter
- `.tres` resources and JSON manifests
- Godot board loading
- Enemy runtime instantiation

That gives us one shared normalization point today, instead of trying to land a full ECS rewrite in one jump.
