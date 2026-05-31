# Enemy And Exit Architecture

This document captures the current runtime and solver boundaries after the enemy-role and escape-zone follow-up cleanup.

## Scope

These rules describe the architecture that exists today.

- The single-cell main exit is still a first-class win cell.
- The 2x2 escape zone is also still a valid win zone.
- The dual-exit "prefer the dedicated main exit when both are valid" question remains open.
- Linked Escape Hunter spawning remains owned by the 2x2 escape zone.

## Exit Terminology

Use these terms consistently across Python and Godot:

- `main exit`: the dedicated single-cell exit authored as `main_exit_cell`.
- `main exit cells`: the authored cells that belong to the dedicated exit footprint. Today this is usually one cell.
- `escape zone`: the authored 2x2 zone that can also end the run and owns zone-linked spawning.
- `win zone cells`: the union of the main-exit cells and the escape-zone cells.
- `escape zone spawners`: board-authored spawn definitions associated with the escape zone.

Compatibility notes:

- Older payloads and resources may still serialize `goal`, `goal_cells`, `exit_cell`, `exit_cells`, and `zone_spawners`.
- Runtime loaders should continue accepting those aliases, but new code should reason in terms of main exit, win zone, and escape-zone spawners.

## Enemy Modeling

Enemy modeling is split into two orthogonal axes:

- `role`: design identity and authored intent, such as `x_chaser`, `y_chaser`, `dasher`, or `linked_escape_hunter`.
- `movement behavior`: the runtime behavior family, such as `greedy`, `astar`, `dash`, `patrol`, or `wander`.

This separation lets us keep old authored aliases readable while still routing behavior through one canonical movement layer.

## Runtime Phases

Enemy processing should stay separated into these responsibilities:

- `activation`: whether an enemy is awake yet.
- `spawn`: whether a delayed or zone-linked enemy can materialize this turn.
- `movement`: how an active enemy chooses cells.
- `contact`: what happens when enemies collide with the player or with each other.
- `lifetime`: when temporary enemies expire after acting.

This is the same conceptual layering used in the Python solver:

- `enemy_activation_rules.py`
- `enemy_spawn_rules.py`
- `enemy_turn_rules.py`
- `enemy_contact_rules.py`

## Escape-Zone Ownership

The board owns escape-zone-linked spawn definitions.

- `MazeData` stores the authored escape-zone cells and escape-zone spawner specs.
- The runtime spawner controller advances countdowns, computes warning tiles, and emits spawn configurations.
- `EnemyManager` remains responsible for instantiated enemies and turn execution, but it should not embed escape-zone schema rules.

This keeps the solver and runtime aligned:

- Python reasons about spawners as board-authored state in `ZoneSpawnerSpec`.
- Godot reasons about spawners as board-authored dictionaries loaded from the same resource data.

## Warning Preview Rules

The yellow warning overlay is a preview of the next successful spawn location, not a permanent marker on every candidate cell.

- A warning appears when a spawner is one enemy turn away from spawning.
- If the selected spawn is blocked, the countdown remains at one turn.
- Because the countdown remains at one turn, the warning should remain available on the next refresh until a spawn succeeds or the candidate set changes.

## What Stays Open

These are intentionally not resolved by the current cleanup:

- Whether dual-exit boards should prefer the dedicated main exit over the escape zone when both are legal wins.
- Any broader procedural-generation retuning beyond preserving the current authored semantics.
- Removing every legacy alias from saved data. Compatibility remains more important than cosmetic purity for now.
