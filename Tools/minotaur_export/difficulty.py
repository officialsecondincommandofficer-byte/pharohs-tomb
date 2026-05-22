from __future__ import annotations

from dataclasses import dataclass

from .models import MazeRecord


@dataclass(frozen=True, slots=True)
class DifficultyAssigner:
    def assign(self, records: list[MazeRecord]) -> dict[MazeRecord, str]:
        if not records:
            return {}

        grouped: dict[tuple[int, int], list[MazeRecord]] = {}
        for record in records:
            grouped.setdefault(record.size, []).append(record)

        labels: dict[MazeRecord, str] = {}
        for group in grouped.values():
            ordered = sorted(group, key=lambda item: item.solution_total_steps)
            top_length = ordered[-1].solution_total_steps
            for index, record in enumerate(ordered):
                if record.solution_total_steps == top_length:
                    labels[record] = "max"
                    continue

                percentile = (index + 1) / max(len(ordered), 1)
                if percentile <= (1.0 / 3.0):
                    labels[record] = "easy"
                elif percentile <= (2.0 / 3.0):
                    labels[record] = "medium"
                else:
                    labels[record] = "hard"

        return labels
