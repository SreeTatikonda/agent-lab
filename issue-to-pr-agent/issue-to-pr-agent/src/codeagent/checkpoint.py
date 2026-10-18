"""Checkpoints after every step so a crashed run resumes instead of restarting.

A checkpoint holds the conversation AND the workspace diff. The conversation alone is not
enough. Files on disk must match what the model believes they contain.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .models import TestReport, Usage


@dataclass
class Checkpoint:
    run_id: str
    task_id: str
    step: int
    messages: list[dict]
    diff: str
    usage: dict
    cost_usd: float
    elapsed_s: float
    baseline: dict | None
    tests_since_edit: bool
    repetition_counts: dict[str, int]

    def usage_obj(self) -> Usage:
        return Usage(**self.usage)

    def baseline_obj(self) -> TestReport | None:
        return TestReport(**self.baseline) if self.baseline else None


class CheckpointStore:
    def __init__(self, directory: str | Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def path(self, run_id: str) -> Path:
        return self.dir / f"{run_id}.json"

    def save(self, cp: Checkpoint) -> None:
        # write then rename, so a crash mid-write never leaves a corrupt checkpoint
        tmp = self.path(cp.run_id).with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(cp), default=_default))
        os.replace(tmp, self.path(cp.run_id))

    def load(self, run_id: str) -> Checkpoint:
        data = json.loads(self.path(run_id).read_text())
        return Checkpoint(**data)


def _default(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    raise TypeError(f"not serializable: {type(obj)}")
