# First Iteration Plan: Pharaoh's Tomb

## Summary
- First Iteration is a playable vertical slice of the vision: one generated floor, strict turn sequencing, grid-based player movement, one-hit death, key-gated exit, turn limit, fog of war, minimal HUD, and enemy turns driven by signals.
- The approved filesystem interpretation is a scene-tree-mapped layout: the vision document's `Main -> GameManager / MazeGenerator / TileMap / FogOfWar / Player / EnemyManager / ItemLayer / HUD` structure becomes the gameplay folder structure.
- `GameManager` is implemented last, after `MazeGenerator`, `Player`, `EnemyManager`, `ItemLayer`, `FogOfWar`, and `HUD` have stable interfaces.
- `Design_Docs/First_Iteration_Plan.md` is the planned destination for this document when implementation begins.
- Current implementation note: the runtime maze now uses thin edge walls between tiles, a tiled perimeter border, randomized board-size presets, and randomized wall-density presets.

## First Iteration Goals
- Deliver a single-floor end-to-end loop: spawn, explore, collect key, unlock exit, escape or die.
- Replace continuous movement with one-turn-at-a-time player actions: `move`, `wait`, and a `use_item` API that supports first-iteration item effects.
- Generate a maze at runtime with a guaranteed valid route from player spawn to key to exit.
- Run enemy actions only after the player completes a turn.
- Show canonical state through UI only: remaining turns, floor number, and inventory.
- Support placeholder-only presentation: current or simple placeholder sprites, no real audio, no save/load, no combat, no cutscenes, no multiplayer.
- Leave the project in a modular state so later iterations can add more floors, scaling, and polish without reorganizing ownership again.

## Target Folder Structure
```text
res://
├── Main/
│   ├── Main.tscn
│   └── main.gd
├── GameManager/
│   ├── GameManager.tscn
│   └── game_manager.gd
├── MazeGenerator/
│   ├── MazeGenerator.tscn
│   ├── maze_generator.gd
│   ├── maze_data.gd
│   └── Resources/
├── TileMap/
│   ├── TileMap.tscn
│   ├── tile_map_controller.gd
│   └── Resources/
├── FogOfWar/
│   ├── FogOfWar.tscn
│   └── fog_of_war.gd
├── Player/
│   ├── Player.tscn
│   ├── player.gd
│   └── Resources/
├── EnemyManager/
│   ├── EnemyManager.tscn
│   ├── enemy_manager.gd
│   ├── enemy_base.gd
│   ├── Chaser/
│   ├── Patroller/
│   └── Wanderer/
├── ItemLayer/
│   ├── ItemLayer.tscn
│   ├── item_layer.gd
│   ├── item_pickup.gd
│   ├── Key/
│   ├── Torch/
│   ├── Freeze/
│   ├── Compass/
│   └── ExtraTurns/
├── HUD/
│   ├── HUD.tscn
│   └── hud.gd
├── Assets/
│   ├── Sprites/
│   ├── Tilesets/
│   ├── UI/
│   └── Materials/
├── Global/
│   └── Autoload/
└── Design_Docs/
    └── First_Iteration_Plan.md
```

## Public Interfaces and Data Contracts
- `MazeGenerator` emits `floor_generated(board_state)` after creating a maze and spawn data.
- `Player` exposes `request_turn_action(action_data)` and emits `turn_finished(turn_result)`.
- `EnemyManager` exposes `begin_enemy_phase(board_state, player_cell)` and emits `enemy_phase_finished(enemy_results)`.
- `ItemLayer` emits `item_collected(item_id)` and `item_used(item_result)`.
- `GameManager` emits `turn_started`, `turn_resolved`, `floor_cleared`, `player_died`, and `run_finished`.
- `board_state` contains at minimum: maze bounds, walkability, spawn cells, exit cell, key cell, enemy spawns, item spawns, and turn limit.
- `board_state` now also carries the selected wall-density value and current grid dimensions so the HUD can report live generation settings.
