# SolverTestMazes

This folder is reserved for the `SolverTestMazes` regression world.

Purpose:
- hold curated exported mazes that exercise solver-heavy scenarios
- provide a stable gameplay regression suite for replay, enemy behavior, and stored solution validation
- complement the Python-side generation benchmark matrix with a fixed world of known stress cases

Planned suite shape:
- `15` mazes total
- `5` baseline/feature mazes
- `5` medium-complexity behavior mazes
- `5` stress mazes

Intended categories:
1. Large sparse boards with long shortest paths
2. Trap-heavy medium boards
3. Multi-enemy cross-pressure boards
4. Killer-enemy collision boards
5. Samurai timing boards
6. Mixed enemy-type large boards
7. Boards where the no-enemy shortest path is unsafe
8. Boards with required waiting
9. Boards with multiple almost-works corridors
10. Large max-stress boards
11. Mechanic probes such as teleports and actor-specific wall layouts
12. ECS bridge validation probes for canonical enemy payloads and runtime-system agreement

Source of truth for the exact planned maze specs and benchmark matrix:
- `Tools/solver_test_mazes_regression_matrix.json`

Current tuning note:
- the samurai timing regression case is intentionally back on an `8x8` board with a shorter minimum path target because the larger issue appears to be low route-length pressure, not lack of space

Related roadmap:
- `Design_Docs/Solver_Generation_Roadmap.md`
- `Design_Docs/ECS_Bridge_Runtime_Validation_Guide.md`

Runtime regression harness:
- `Tools/GodotRuntimeRegression.tscn` and `Tools/godot_runtime_regression.gd` run headless undo/reset/replay checks against curated runtime boards
- prefer adding restore/replay regressions there when the issue is about runtime-state ownership rather than solver generation
- keep the harness focused on canonical gameplay flow, not visual presentation timing

When the mazes are generated:
- exported `.tres` files should live in this world folder or an imported manifest path associated with this folder
- add a `world_manifest.json` that points at the curated resources
- keep the level ids stable so replay and regression references do not drift
- keep escape-zone and dual-exit probes under this world tree instead of mixing active manifest references back through `Resources/Test`

Wall mechanics note:
- actor-specific wall probes should prefer small curated layouts first because they exercise runtime legality without inflating solver state
- one-way passage probes should stay small too, with at least one case that forces reverse-search helpers to respect directed movement
- use `player-only` to mean only the player can pass through the edge, and `enemy-only` to mean only enemies can pass through it
- locked-passage probes should not be added to procedural generation flows until gated-reachability validation exists explicitly

Escape-zone note:
- dual-exit probes should explicitly call out whether the stored solution reaches the dedicated main exit or the 2x2 escape zone
- keep at least one authored regression board that still wins through the 2x2 zone until the main-exit preference question is intentionally resolved

ECS bridge note:
- `Probes/ECSBridge` contains validation boards used to confirm Python export data and Godot runtime systems still agree after the ECS/component migration work
- these probes should remain small, intentional, and scenario-focused rather than becoming general content levels
- if a runtime-system regression appears in enemy behavior, spawner timing, or turn-end teleport handling, add or update a probe here before broadening generation coverage
