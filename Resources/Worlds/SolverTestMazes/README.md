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

Source of truth for the exact planned maze specs and benchmark matrix:
- `Tools/solver_test_mazes_regression_matrix.json`

Current tuning note:
- the samurai timing regression case is intentionally back on an `8x8` board with a shorter minimum path target because the larger issue appears to be low route-length pressure, not lack of space

Related roadmap:
- `Design_Docs/Solver_Generation_Roadmap.md`

When the mazes are generated:
- exported `.tres` files should live in this world folder or an imported manifest path associated with this folder
- add a `world_manifest.json` that points at the curated resources
- keep the level ids stable so replay and regression references do not drift
