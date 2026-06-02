# pharohs-tomb

This project is now a Godot 4.x adaptation of **Theseus and the Minotaur**, using the repo's existing pixel-art board presentation and thin-wall maze style.

## Runtime Architecture

- Python and Godot now share a canonical enemy schema:
  `Resources/DataSchemas/enemy_ecs_schema.json`
- Enemy payloads are normalized through a long compatibility bridge that still accepts legacy `role`, `movement_type`, and `traits`.
- Godot runtime behavior is now largely organized as:
  `record -> registry -> system -> view`
- The main migrated slices are:
  enemy runtime records and systems,
  zone spawner runtime records and systems,
  board interaction systems for teleports, actor-specific walls, and turn-end transitions,
  and a world runtime registry that keeps player state, typed enemy/spawner runtime payloads, and turn snapshots in canonical runtime state.

Useful architecture docs:

- `Design_Docs/ECS_Component_Migration_Plan.md`
- `Design_Docs/ECS_Bridge_Runtime_Validation_Guide.md`
- `Design_Docs/Runtime_Architecture.md`

## Current Playable Loop

- Move one tile or wait.
- The Minotaur moves up to two steps after every valid player action.
- Reach the goal before the Minotaur catches you.
- Undo the last turn, reset the board, reroll a new maze, or replay the shortest solution.
- Save the current generated maze as a Godot resource under `user://saved_mazes/`.

## Current Maze Runtime

- Boards are generated at runtime from connected edge-wall layouts.
- The generator follows a board-plus-solver workflow inspired by the reference Python repo.
- Solvable candidates are grouped by solution length and selected by difficulty bucket.
- Runtime board interaction rules are shared through explicit systems instead of being spread only across scene/controller logic.
- MongoDB and precomputed maze retrieval are intentionally out of scope.
- Save support is v1 and hotkey-only for now; loading and save browsing are intentionally deferred.

## Current HUD

The HUD shows:

- board dimensions
- size bucket
- difficulty bucket
- moves taken
- shortest solution length
- current game status

## Controls

- `Arrow Keys`: move
- `Space`: wait
- `Shift`: undo
- `Backspace`: reset current board
- `P`: show shortest solution
- `K`: save the current generated maze to `user://saved_mazes/`
- `R`: reroll a new board
