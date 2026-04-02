# pharohs-tomb

Pharaoh's Tomb is a top-down, turn-based Godot 4.x maze game built in GDScript.

## Current Playable Loop

- Move one tile per turn, wait, or use an item.
- Enemies act only after the player consumes a turn.
- Find the key, unlock the exit, and escape before turns run out.
- Contact with an enemy is instant death.

## Current Maze Runtime

- Floors randomize among multiple board sizes, currently `8x8`, `10x10`, `16x16`, and a larger default board.
- Interior walls are thin wall segments placed between tiles instead of full blocked wall cells.
- The perimeter is gameplay-blocking but rendered visually as a tiled border.
- Wall density is chosen per floor from preset coverage values: `33%`, `40%`, or `50%`.
- Some walls can attach directly to the perimeter so layouts feel connected to the frame.

## Current HUD

The HUD shows:

- Floor number
- Grid size
- Wall percentage for the current floor
- Remaining turns
- Key state
- Inventory

## Notes

The project is still in active gameplay tuning, but the current build is playable end-to-end.
