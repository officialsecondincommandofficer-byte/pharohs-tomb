# Solver And Generation Roadmap

This document captures the intended roadmap for Pharaoh's Tomb maze solving and maze generation as mechanics become more complex.

## Goals

- prevent endless generation loops
- keep solver and generation architecture understandable
- support curated solver-proven content and future random unsolved content
- prepare for future mechanics such as teleports, multi-floor maps, cube mazes, treadmills, moving platforms, and more enemy types
- define when a native compiled solver core becomes warranted

## Near-Term Priorities

### 1. Bounded generation

Every generation job should have hard limits and explicit failure modes.

Recommended limits:
- `max_attempts`
- `max_board_seeds`
- `max_runtime_seconds`
- optional `max_states_explored`

Generation should return explicit outcomes such as:
- `solved_and_exported`
- `no_candidate_within_budget`
- `candidate_failed_validation`
- `search_budget_exceeded`

### 2. Better observability

Generation and benchmark flows should continue reporting:
- attempts
- layouts tried
- board seeds tried
- rejections
- accepted records
- total runtime

This keeps expensive specs diagnosable without changing solver behavior.

### 3. Regression split

Keep three categories distinct:
- curated verified regression mazes
- manual probe mazes
- benchmark-only stress specs

`Resources/Worlds/SolverTestMazes` is the main home for this discipline.

## Medium-Term Architecture

### 1. Formal state model

The state model should remain explicit and mechanic-oriented.

Expected dimensions over time:
- player position
- enemy positions
- enemy runtime states
- floor / level index
- teleport destination effects
- falling / drop resolution state
- treadmill offsets
- moving platform phase
- cube face or inside/outside mode

### 2. Transition model

Search should continue depending on a clean transition layer rather than embedding mechanic rules inside BFS logic.

Preferred transition order:
1. player move
2. immediate terrain effects
3. enemy phase
4. teleports / falls / floor transitions
5. hazard validation

Teleport rule for the current exported-board model:
- the player first steps onto the teleport source tile
- the enemy phase targets that stepped/source tile, not the destination
- if the player survives the enemy phase, the teleport resolves to the destination
- waiting on a teleport tile also re-triggers that same teleport after the enemy phase
- exit and trap validation happen against the resolved destination after the warp

Recommended naming:
- `stepped_cell`: the location reached by ordinary movement before teleport resolution
- `resolved_cell`: the final player location after teleport resolution

This keeps teleport timing explicit in both the Python solver transition layer and the Godot runtime turn resolver.

### 3. Search modes

We should support multiple generation/search modes rather than forcing one global policy:
- `solver_proven_curated`
- `random_variety`
- `stress_benchmark`
- `manual_probe`

This matters because late-game random content may not need full solver proof in every case.

## Search Strategy Direction

We should prioritize:
- bounded search
- reusable state/transition modeling
- measured regression coverage

We should avoid:
- heuristics that create trivially safe player bubbles
- heuristics that push enemies unrealistically far away
- generation shortcuts that make mazes solver-friendly but uninteresting

If performance work continues, the safest direction is:
1. better budgets
2. better metrics
3. optional staged rejection
4. only then deeper search/runtime optimization

## Future Mechanics Order

Recommended order of complexity growth:
1. teleports
2. multi-floor layouts with falling
3. additional enemy types
4. treadmills / shifting columns
5. moving platforms
6. cube inside/outside topology

This order keeps topology changes ahead of fully dynamic board-state changes.

## Native Core Flags

The following should be treated as explicit signals that a native compiled solver core is becoming warranted.

### Flag 1: Routine generation stays too expensive

Curated solver-proven generation regularly takes many minutes per maze even after spec tuning and generation budgets.

### Flag 2: State complexity becomes multi-system

Search state must simultaneously encode several dynamic systems such as:
- enemy runtime state
- teleports or floor transitions
- treadmill/platform phase
- cube face / inside-outside state

### Flag 3: Python overhead dominates profiles

Profiling shows most time concentrated in:
- state creation
- hashing / visited-state checks
- transition simulation
- BFS expansion

### Flag 4: Runtime-generated solvable content becomes common

If gameplay starts depending on frequent runtime-generated solvable mazes rather than offline export, a native core becomes much more attractive.

### Flag 5: Compact state encoding becomes necessary

If we need packed states, specialized memory layouts, or advanced visited-state handling to stay practical, Python is likely no longer the best long-term core.

## Native Core Plan

When the time comes, the intended split should be:

Python keeps:
- orchestration
- benchmark tooling
- export pipelines
- manifest/resource generation
- regression automation

Native core owns:
- state encoding
- transition simulation
- search
- validation

Candidate implementation languages:
- Rust for safety and maintainability
- C++ for direct control and easier native/Godot-adjacent expectations

## Standing Guidance

When evaluating future feature requests, call out Native Core Flags whenever a requested mechanic materially increases dynamic search state or solver cost.

Features that should trigger that conversation quickly:
- cube mazes
- moving platforms
- treadmills / shifting columns
- many interacting enemy types
- frequent runtime-generated solvable mazes
- item-aware search requirements

Features that usually do not require that conversation immediately:
- one new mostly static enemy type
- teleports only
- simple two-floor fall-through maps
- more curated exported levels
