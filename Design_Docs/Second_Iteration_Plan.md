# Second Iteration Plan: Pharaoh's Tomb

## Summary

- Second Iteration turns the current playable vertical slice into a stable, replayable short run.
- The main target is not "more random features." The target is stronger ownership, cleaner orchestration, multi-floor progression, better gameplay readability, and safer tuning hooks.
- `GameManager` remains the owner of turn sequencing, win/lose rules, and floor progression.
- `MazeGenerator` remains the owner of layout, walkability, and spawn output.
- `EnemyManager` remains the owner of enemy turn execution after player resolution.
- `HUD` remains a reader of canonical state rather than a second source of truth.
- Transitional startup scaffolding may stay temporarily, but any responsibility moved out of it must be documented during implementation.

## Second Iteration Theme

Version 1 proved the game loop can work. Version 2 should make that loop dependable and worth replaying.

That means:

- floors should scale in a controlled way instead of feeling like isolated test boards
- the run should communicate state clearly
- item, enemy, and generation systems should expose tuning hooks instead of hard-coded behavior scattered across scenes
- subsystem ownership should be clearer so future work does not pile onto bootstrap scripts

## Second Iteration Goals

- Deliver a short multi-floor run instead of a one-floor-only victory structure.
- Add controlled floor scaling for board size, turn pressure, item distribution, and enemy composition.
- Stabilize canonical runtime data so all gameplay-facing systems read the same floor and run state.
- Improve moment-to-moment readability with clearer HUD, status messaging, and fog or exit feedback.
- Keep item usage tactical and easy to understand.
- Preserve the current no-combat identity: evade, route-plan, collect, and escape.
- Leave the project ready for a later polish pass without needing another architecture reset.

## Non-Goals

- No combat system.
- No save/load.
- No multiplayer.
- No cutscenes.
- No full audio production.
- No broad menu or meta-progression expansion unless explicitly requested later.
- No shift away from grid-based, turn-based play.

## Version 2 Milestone Outcome

At the end of Second Iteration, the player should be able to start a run, clear several escalating floors, understand the current danger and resource state at a glance, and restart cleanly after a win or loss.

## Implementation Priorities

### 1. Architecture Stabilization

- Confirm `GameManager` as the single runtime owner for:
  - current floor index
  - total floors in the run
  - remaining turns
  - temporary item effects
  - run success or failure
- Reduce accidental orchestration leakage from transitional scripts.
- Keep startup functional while documenting any responsibility moved from:
  - `src/GameRunner/game_runner.gd`
  - `src/Stages/base_stage.gd`
  - `Global/Managers/scene_manager.gd`
  - `Main/Scripts/Main.gd`

### 2. Multi-Floor Run Progression

- Expand from a single-floor success state to a short run structure.
- Recommended baseline:
  - `3` floors minimum for a complete run
  - scaling per floor instead of fully random difficulty spikes
- Floor clear should transition into the next generated floor until the run is won or lost.
- The final floor should end the run cleanly with an explicit victory state.

### 3. Controlled Difficulty Scaling

- Move from mostly flat randomness to guided scaling.
- Scale by floor:
  - board size band
  - wall density band
  - turn-limit pressure
  - enemy count
  - enemy type mix
  - item spawn frequency
- Preserve solvability and route clarity as higher priority than raw difficulty.
- Avoid making later floors harder only by starving the player of turns.

### 4. Item And State Readability

- Keep the current item set, but make their state easier to read and tune.
- Temporary effects should have canonical durations owned by `GameManager`.
- HUD should communicate:
  - active temporary effects
  - remaining duration where applicable
  - key state
  - floor progress
  - inventory contents
- Status feedback should explain why something happened when possible:
  - exit unlocked
  - freeze active
  - torch active
  - extra turns added
  - run lost because of contact or timeout

### 5. Enemy And Generation Tuning Pass

- Keep the current enemy families, but make spawn composition intentional.
- Recommended floor-based enemy rollout:
  - early floors emphasize readable threats
  - later floors combine behaviors that create routing pressure
- `MazeGenerator` should expose stable data for:
  - player spawn
  - exit cell
  - key cell
  - item spawns
  - enemy spawn entries with type metadata
- Prefer tuning spawn rules and board pressure before introducing expensive runtime validation systems.

### 6. QA And Debug Support

- Add lightweight debug or verification support for:
  - current floor number
  - chosen board dimensions
  - wall density
  - turn limit
  - enemy composition
  - item spawn summary
- Record a simple manual test checklist for full-run verification.
- Keep debug support lightweight and removable, not permanent production clutter.

## Recommended Delivery Order

This iteration should still follow the agent handoff model from `AGENTS.md`, but with a v2 focus:

1. Lead Architect Agent
   - lock the run-state shape
   - confirm which transitional scaffolding remains for now
   - define floor progression interfaces
2. Core Gameplay Agent
   - confirm player action flow still behaves correctly across multi-floor transitions
   - ensure item-use and action lock rules remain clean
3. World Generation Agent
   - implement floor-scaling rules and stable generation output contracts
4. Enemy Systems Agent
   - implement floor-based enemy composition and enemy-phase tuning
5. Presentation and UX Agent
   - improve HUD, status visibility, and floor-transition readability
6. QA and Devtools Agent
   - verify full-run stability and produce repeatable regression notes

## Public Interfaces And Data Contracts

Second Iteration should preserve small, narrow interfaces:

- `MazeGenerator.generate_floor(floor_index)` returns canonical board data for that floor.
- `Player.request_turn_action(action_data)` remains the single player-turn entry point.
- `Player.turn_finished(turn_result)` remains the signal that hands control back to orchestration.
- `EnemyManager.begin_enemy_phase(player_cell)` remains the phase entry point, but should consume canonical board and spawn state rather than hidden scene assumptions.
- `EnemyManager.enemy_phase_finished(enemy_results)` remains the end-of-phase handoff.
- `HUD.update_state(game_state)` should receive canonical values from `GameManager`, not reconstruct them locally.

Recommended additions to canonical runtime state:

- `run_floor_index`
- `run_total_floors`
- `active_effects`
- `enemy_spawn_table`
- `item_spawn_table`
- `difficulty_profile_id` or equivalent floor-scaling metadata

## Success Criteria

Second Iteration is done when all of the following are true:

- A full short run can be played across multiple floors without manual scene intervention.
- Turn flow remains strictly player phase followed by enemy phase.
- Floor progression is handled by `GameManager` rather than ad hoc scene logic.
- Difficulty scaling feels deliberate rather than purely random.
- HUD and status messaging reflect canonical runtime state.
- Item durations and run state are easy to inspect during testing.
- Transitional scaffolding either still has a clear bootstrap-only role or has had ownership moved out of it with notes.

## Manual Validation Checklist

- Start a new run and clear floor 1.
- Confirm floor 2 loads without stale state from the previous floor.
- Verify key collection, exit unlock, and floor clear still work on later floors.
- Verify freeze, torch, compass, and extra-turn effects behave correctly across turns.
- Confirm enemy phases still do not run until the player consumes a turn.
- Lose by enemy contact and verify restart behavior.
- Lose by turn timeout and verify restart behavior.
- Win the final floor and verify end-of-run messaging.
- Confirm HUD values match actual game state on every floor.

## Known Follow-Ups After Version 2

- deeper generation survivability validation if tuning alone is not enough
- stronger presentation polish
- more varied floor themes or environmental flavor
- expanded enemy behaviors only if the existing loop remains readable

## Suggested File Destination

This document belongs in:

- `pharohs-tomb/Design_Docs/Second_Iteration_Plan.md`

That keeps it beside Version 1 planning documents and preserves the current documentation pattern already used by the project.
