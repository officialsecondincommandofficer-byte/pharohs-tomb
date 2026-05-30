from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .models import ExportedMaze, GenerationConfig


@dataclass(slots=True)
class ManifestWriter:
    time_provider: Callable[[], float] = field(default=time.time)

    def write(self, manifest_path: Path, config: GenerationConfig, generated_records: list[ExportedMaze]) -> None:
        manifest = {
            "source_project": str(config.source_project),
            "output_dir": str(config.output_dir),
            "generated_at_unix": int(self.time_provider()),
            "parameters": {
                "width": config.width,
                "height": config.height,
                "iterations": config.iterations,
                "mazes_per_iteration": config.mazes_per_iteration,
                "min_moves": config.min_moves,
                "seed": config.seed,
                "cell_size": config.cell_size,
                "enemy_move_priority": config.enemy_move_priority,
                "greedy_horizontal_count": config.greedy_horizontal_count,
                "greedy_vertical_count": config.greedy_vertical_count,
                "samurai_count": config.samurai_count,
                "killer_count": config.killer_count,
                "trap_count": config.trap_count,
                "player_only_wall_count": config.player_only_wall_count,
                "enemy_only_wall_count": config.enemy_only_wall_count,
                "additional_checks": config.additional_checks,
                "additional_check_threshold": config.additional_check_threshold,
            },
            "files": [
                {
                    "file_name": exported.path.name,
                    "path": str(exported.path),
                    "width": exported.record.width,
                    "height": exported.record.height,
                    "solution_total_steps": exported.record.solution_total_steps,
                    "difficulty_category": exported.difficulty_label,
                    "iteration": exported.record.iteration,
                    "player_only_walls": [[list(a), list(b)] for a, b in exported.record.player_only_walls],
                    "enemy_only_walls": [[list(a), list(b)] for a, b in exported.record.enemy_only_walls],
                    "teleport_pairs": [
                        {
                            "a": list(pair.a),
                            "b": list(pair.b),
                        }
                        for pair in exported.record.teleport_pairs
                    ],
                    "enemy_teleport_pairs": [
                        {
                            "a": list(pair.a),
                            "b": list(pair.b),
                        }
                        for pair in exported.record.enemy_teleport_pairs
                    ],
                    "shared_teleport_pairs": [
                        {
                            "a": list(pair.a),
                            "b": list(pair.b),
                        }
                        for pair in exported.record.shared_teleport_pairs
                    ],
                    "trap_cells": [list(cell) for cell in exported.record.trap_cells],
                    "player_start": list(exported.record.player_start),
                    "enemy_spawns": [
                        {
                            "type": enemy.enemy_type,
                            "cell": list(enemy.cell),
                            "move_priority": enemy.move_priority,
                            "step_count": enemy.step_count,
                            "facing_index": enemy.facing_index,
                            "traits": list(enemy.traits),
                        }
                        for enemy in exported.record.enemy_spawns
                    ],
                    "minotaur_start": list(exported.record.minotaur_start),
                    "goal": list(exported.record.goal),
                }
                for exported in generated_records
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
