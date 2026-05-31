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

Optional TODO for dual-exit boards:
- decide whether the solver/generator should prefer the dedicated main exit when both the main exit and a 2x2 escape zone are valid win cells
- keep at least one curated board where the currently solver-preferred path wins via the 2x2 zone, because it is a useful behavior probe

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

## Wall Mechanics Foundation

Wall mechanics should stay split by responsibility rather than getting folded into one broad "movement rules" bucket.

Recommended ownership:
- board/layout representation owns which edges exist and which actor classes those edges block
- movement legality / transitions owns how a player or enemy tests one attempted step against that layout
- solver state transitions own only mechanic state that actually changes over time
- export format owns a lossless serialized description of shared walls plus any actor- or state-specific wall layers
- Godot runtime loading and gameplay behavior own replaying the same legality rules during play, not redefining them
- regression coverage owns explicit probes for each new wall family plus at least one playable curated level

### Mechanic Categories

#### 1. One-way walls or actor-specific walls

These are the safest first expansion because they are still topology-centric.

Actor-specific walls:
- change which actor class may traverse an edge
- do not add per-turn or per-state memory
- fit the current solver architecture cleanly because legality can stay in the transition layer

Recommended naming:
- `player_only_walls`: only the player may pass through these edges
- `enemy_only_walls`: only enemies may pass through these edges

One-way walls:
- are also static topology, but they make the graph directed
- require more care in reverse-distance helpers and predecessor logic
- remain lower risk than stateful mechanics, but are slightly more invasive than actor-specific walls

#### 2. Breakable walls

Breakable walls are a stateful transition mechanic.

They require:
- tracking which walls have already been broken
- deciding whether enemies can break them too
- expanding solver state to encode board mutation

This is the point where wall mechanics stop being "just topology" and start materially increasing dynamic solver state.

#### 3. Locked passages, gates, or keyed barriers

Locked passages are allowed as a design mechanic, including cases where they fully enclose an area or the exit, but generation and validation must treat that as explicit gated access rather than ordinary reachability.

Required rule:
- a locked enclosure is valid only if the gating condition is modeled and validated end to end

This means we must not treat "the exit is unreachable in the base graph" as automatically invalid once locked passages exist, but we also must not silently allow unreachable exits when no valid unlock path exists.

### Generation Implications

Static topology changes:
- shared walls
- actor-specific walls
- one-way walls

These change graph shape but do not change solver memory size by themselves.

Stateful transition changes:
- breakable walls
- locked passages that unlock mid-run
- gates driven by switches, items, or triggers

These change both graph behavior and the search state space.

Guardrail for locked enclosures:
- allowing the exit to sit behind locked passages is dangerous if generation still assumes plain reachability from the start state
- without explicit gating validation, generation can export mazes that look deliberate but are actually impossible or misleading
- the risk is higher than teleports because the invalidity can hide behind a seemingly reasonable outer layout

Recommended policy:
- curated content: allowed once the unlock condition is explicit and solver-validated
- procedural generation: disallowed by default until generation has a dedicated gated-reachability validator and an explicit opt-in rule

In practice, generation should require:
- a base-state reachability check
- a post-unlock reachability check
- proof that the unlock path itself is achievable without circular dependence
- explicit reporting when an exit is enclosed behind a locked passage

### Recommended Implementation Order

1. Actor-specific walls
2. One-way walls
3. Locked passages / gates
4. Breakable walls

Why:
- actor-specific walls preserve the current solver architecture best
- one-way walls are still static but require directed-graph care
- locked passages are where generation correctness risk becomes much sharper, especially around enclosed exits
- breakable walls materially increase dynamic solver state and should come only after the transition/state model is ready

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
