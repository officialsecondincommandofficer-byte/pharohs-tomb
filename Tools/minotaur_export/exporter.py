from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .grid import partition_walls
from .models import Coord, EnemySpawn, ExportedMaze, MazeRecord


def vector2i(value: Coord) -> str:
    return f"Vector2i({value[0]}, {value[1]})"


def vector2i_array(values: Iterable[Coord]) -> str:
    serialized = ", ".join(vector2i(value) for value in values)
    return f"Array[Vector2i]([{serialized}])"


def string_array(values: Iterable[str]) -> str:
    serialized = ", ".join(json.dumps(value) for value in values)
    return f"Array[String]([{serialized}])"


def enemy_spawn_dictionary(enemy: EnemySpawn) -> str:
    values = [
        f'"type": {json.dumps(enemy.enemy_type)}',
        f'"cell": {vector2i(enemy.cell)}',
        f'"move_priority": {json.dumps(enemy.move_priority)}',
        f'"step_count": {enemy.step_count}',
        f'"facing_index": {enemy.facing_index}',
    ]
    if enemy.traits:
        values.append(f'"traits": {string_array(enemy.traits)}')
    return "{%s}" % ", ".join(values)


def enemy_spawn_array(values: Iterable[EnemySpawn]) -> str:
    serialized = ", ".join(enemy_spawn_dictionary(value) for value in values)
    return f"Array[Dictionary]([{serialized}])"


@dataclass(frozen=True, slots=True)
class GodotMazeExporter:
    resource_script_path: str = "res://MazeGenerator/saved_maze_resource.gd"

    def build_display_name(self, saved_at_unix: int, width: int, height: int, difficulty_label: str, index: int) -> str:
        stamp = datetime.fromtimestamp(saved_at_unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"{stamp} {width}x{height} {difficulty_label.capitalize()} #{index:03d}"

    def build_file_name(self, saved_at_unix: int, width: int, height: int, steps: int, difficulty_label: str, index: int) -> str:
        stamp = datetime.fromtimestamp(saved_at_unix, tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"minotaur_{stamp}_{width}x{height}_len{steps:03d}_{difficulty_label}_{index:03d}.tres"

    def serialize(
        self,
        record: MazeRecord,
        saved_at_unix: int,
        difficulty_label: str,
        index: int,
        generation_profile_id: str,
        cell_size: int,
    ) -> str:
        horizontal_walls, vertical_walls = partition_walls(record.walls)
        display_name = self.build_display_name(saved_at_unix, record.width, record.height, difficulty_label, index)

        lines = [
            '[gd_resource type="Resource" script_class="SavedMazeResource" load_steps=2 format=3]',
            "",
            f'[ext_resource type="Script" path="{self.resource_script_path}" id="1_hji17"]',
            "",
            "[resource]",
            'script = ExtResource("1_hji17")',
            "version = 1",
            f"display_name = {json.dumps(display_name)}",
            f"saved_at_unix = {saved_at_unix}",
            f"width = {record.width}",
            f"height = {record.height}",
            f"cell_size = {cell_size}",
            f"size_category = {json.dumps(record.size_category)}",
            f"difficulty_category = {json.dumps(difficulty_label)}",
            f"horizontal_walls = {vector2i_array(horizontal_walls)}",
            f"vertical_walls = {vector2i_array(vertical_walls)}",
            f"trap_cells = {vector2i_array(record.trap_cells)}",
            f"player_spawn = {vector2i(record.player_start)}",
            f"enemy_spawns = {enemy_spawn_array(record.enemy_spawns)}",
            f"minotaur_spawn = {vector2i(record.minotaur_start)}",
            f"exit_cell = {vector2i(record.goal)}",
            f"solution_actions = {string_array(record.solution)}",
            f"solution_total_steps = {record.solution_total_steps}",
            'generation_mode = "IMPORTED_MINOTAUR_PROJECT"',
            f"generation_profile_id = {json.dumps(generation_profile_id)}",
            "",
        ]
        return "\n".join(lines)

    def write_record(
        self,
        record: MazeRecord,
        output_dir: Path,
        saved_at_unix: int,
        difficulty_label: str,
        index: int,
        generation_profile_id: str,
        cell_size: int,
    ) -> ExportedMaze:
        file_name = self.build_file_name(
            saved_at_unix=saved_at_unix,
            width=record.width,
            height=record.height,
            steps=record.solution_total_steps,
            difficulty_label=difficulty_label,
            index=index,
        )
        file_path = output_dir / file_name
        file_path.write_text(
            self.serialize(
                record=record,
                saved_at_unix=saved_at_unix,
                difficulty_label=difficulty_label,
                index=index,
                generation_profile_id=generation_profile_id,
                cell_size=cell_size,
            ),
            encoding="utf-8",
        )
        return ExportedMaze(path=file_path, record=record, difficulty_label=difficulty_label)
