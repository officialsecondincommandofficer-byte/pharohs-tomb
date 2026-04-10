# pharohs-tomb

This project is now a Godot 4.x adaptation of **Theseus and the Minotaur**, using the repo's existing pixel-art board presentation and thin-wall maze style.

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
