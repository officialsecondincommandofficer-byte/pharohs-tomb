# Survivability Validation Backlog

## Goal

Keep a future-facing design for generation-time seed validation without paying the runtime cost right now.

The idea is to add a lightweight heuristic validator after `MazeGenerator` builds a candidate floor and before the floor is handed to `GameManager`. The validator should filter out obviously bad seeds, not prove every accepted seed is guaranteed winnable.

## Proposed Runtime Shape

- Add a helper under `MazeGenerator`, such as `seed_validator.gd`.
- Entry point:
  - `validate(board_state: MazeData) -> Dictionary`
- Suggested return shape:
  - `{ "passed": bool, "reason": String, "expanded_states": int, "path": Array }`
- Integrate it into `MazeGenerator.generate_floor()` as an optional validation pass after topology is known.
- If validation fails, regenerate up to a fixed attempt cap.
- If the attempt cap is exceeded, fall back to the best topologically valid floor and log a warning.

## Search Model

- Use a danger-aware A* or best-first search rather than exhaustive solving.
- Model only survival-relevant player actions:
  - move in 4 directions
  - wait
  - use `freeze`
  - use `extra_turns`
- Ignore `torch` and `compass` during validation because they change visibility and player information, not basic board survivability.

Suggested compact state:

- player cell
- turns remaining
- enemy turn index
- has key
- collected mask for survival items on the map
- inventory mask for collected-but-unused survival items
- freeze turns remaining

## Threat Heuristics

- `chaser`:
  - precompute earliest-arrival data from spawn with BFS
  - use immediate interception windows as lethal
  - use near-future arrival as a soft penalty
- `patroller`:
  - precompute exact position per turn for a capped horizon
  - current tile is lethal, adjacent tiles are risky
- `wanderer`:
  - use a pessimistic short-horizon threat cloud
  - current and adjacent possible tiles are risky or lethal depending on horizon

## Important Caveat

The previous implementation attempt compiled and worked, but it made floor generation feel too slow and too conservative in practice. If we revisit this, the next pass should start with stricter performance measurement and lighter heuristics before reintroducing runtime validation.

## Recommended Next Workshop Questions

- Should this run on every generated floor or only on later floors?
- Should validation be runtime-only, QA-only, or hybrid?
- What is an acceptable per-floor time budget in milliseconds?
- Do we want a seed filter, a “good enough” solver, or a stronger forced-win guarantee?
- Should enemy placement rules be tightened first before bringing back path search?
