# ECS Bridge Runtime Validation Guide

Use the generated probe pack to verify that the Python solver/export path and the Godot runtime still agree after the component-first bridge migration.

## Probe Pack

Run:

```powershell
python Tools/generate_ecs_bridge_validation_pack.py
```

This writes probe resources under:

- `Resources/Worlds/SolverTestMazes/Probes/ECSBridge`
- `Resources/Worlds/SolverTestMazes/Probes/ECSBridge/ecs_bridge_validation_manifest.json`

## What To Check In Godot

For each generated board:

1. Open the `.tres` and confirm enemy dictionaries contain:
   `canonical_archetype`, `ecs_schema_version`, and legacy fields together.
2. Play the board and confirm the runtime behavior matches the scenario notes in the manifest.
3. Save/restore or reload the board if that workflow is available and verify enemy and spawner state survive correctly.
4. If the board includes teleports or escape-zone spawners, verify turn-end transitions still match the Python solver behavior.

## Scenario Focus

### Greedy / Samurai

- Greedy chasers should still follow their horizontal or vertical priority.
- Samurai should still rotate, detect, charge, and dash correctly.

### Patroller / Stationary / Wanderer

- Patroller should follow its route and loop/ping-pong mode from components.
- Stationary blocker should remain still.
- Wanderer should honor seeded movement and facing from components.

### Escape-Zone Linked Hunter

- Escape-zone spawner should warn and spawn as expected.
- Linked hunter should use A* behavior and temporary lifetime rules correctly.

## Current Runtime Shape

The validation pack now covers more than the original enemy bridge. A passing run gives confidence in:

- shared schema normalization
- enemy runtime records, registries, and systems
- zone spawner runtime records and systems
- board interaction system handling turn-end teleports and movement legality

## Architecture Read

If these probes pass, the bridge is doing the right thing architecturally:

- scalable: behavior selection comes from canonical data instead of ad hoc call sites
- modular: schema, solver systems, runtime systems, and scenes stay separable
- single responsibility: authored intent, behavior execution, and presentation each keep a narrower job
