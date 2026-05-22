from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .difficulty import DifficultyAssigner
from .exporter import GodotMazeExporter
from .generator import MazeGenerator
from .manifest import ManifestWriter
from .models import ExportSummary, GenerationConfig, MazeRecord


@dataclass(slots=True)
class ExportService:
    generator: MazeGenerator
    difficulty_assigner: DifficultyAssigner
    exporter: GodotMazeExporter
    manifest_writer: ManifestWriter
    logger: Callable[[str], None] = print
    time_provider: Callable[[], float] = time.time
    now_provider: Callable[[], datetime] = datetime.now

    def run(self, config: GenerationConfig) -> ExportSummary:
        output_dir = config.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        self.logger(f"Source project: {config.source_project}")
        self.logger(f"Output directory: {output_dir}")
        self.logger(
            "Generating mazes with width=%d height=%d iterations=%d mazes_per_iteration=%d min_moves=%d seed=%s"
            % (
                config.width,
                config.height,
                config.iterations,
                config.mazes_per_iteration,
                config.min_moves,
                config.seed if config.seed is not None else "random",
            )
        )

        all_records: list[MazeRecord] = []
        for iteration in range(1, config.iterations + 1):
            self.logger(f"Iteration {iteration}/{config.iterations}: generating solvable mazes...")
            batch = self.generator.generate_batch(
                width=config.width,
                height=config.height,
                min_moves=config.min_moves,
                target_count=config.mazes_per_iteration,
                iteration=iteration,
                additional_checks=config.additional_checks,
                additional_check_threshold=config.additional_check_threshold,
            )
            all_records.extend(batch)
            self.logger(f"Iteration {iteration}/{config.iterations}: exported {len(batch)} solvable mazes.")

        difficulty_labels = self.difficulty_assigner.assign(all_records)
        saved_at_unix = int(self.time_provider())
        exported_mazes = []

        ordered_records = sorted(
            all_records,
            key=lambda item: (
                item.iteration,
                item.solution_total_steps,
                item.goal,
                item.player_start,
                item.minotaur_start,
            ),
        )
        for index, record in enumerate(ordered_records, start=1):
            exported_mazes.append(
                self.exporter.write_record(
                    record=record,
                    output_dir=output_dir,
                    saved_at_unix=saved_at_unix + index - 1,
                    difficulty_label=difficulty_labels[record],
                    index=index,
                    generation_profile_id=config.generation_profile_id,
                    cell_size=config.cell_size,
                )
            )

        manifest_name = self.now_provider().strftime("minotaur_export_manifest_%Y%m%d_%H%M%S.json")
        manifest_path = output_dir / manifest_name
        self.manifest_writer.write(manifest_path=manifest_path, config=config, generated_records=exported_mazes)

        self.logger(f"Wrote {len(exported_mazes)} maze resources.")
        self.logger(f"Manifest: {manifest_path}")
        return ExportSummary(exported_mazes=tuple(exported_mazes), manifest_path=manifest_path)
