"""Core entities. A Run is a durable state machine, not a request."""
from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


class RunStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StopReason(str, enum.Enum):
    FINISHED = "finished"
    GAVE_UP = "gave_up"
    MAX_STEPS = "max_steps"
    MAX_COST = "max_cost"
    MAX_TIME = "max_time"
    LOOP_DETECTED = "loop_detected"
    BASELINE_BROKEN = "baseline_broken"
    VERIFICATION_FAILED = "verification_failed"


@dataclass
class Budgets:
    max_steps: int = 40
    max_cost_usd: float = 5.0
    max_seconds: float = 1800.0
    warn_at_fraction: float = 0.75


@dataclass
class Pricing:
    """USD per million tokens. Illustrative defaults, override for your model."""
    input_per_m: float = 3.0
    cached_input_per_m: float = 0.30
    output_per_m: float = 15.0

    def cost(self, usage: "Usage") -> float:
        fresh = max(usage.input_tokens - usage.cached_input_tokens, 0)
        return (
            fresh * self.input_per_m
            + usage.cached_input_tokens * self.cached_input_per_m
            + usage.output_tokens * self.output_per_m
        ) / 1_000_000


@dataclass
class Usage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0

    def add(self, other: "Usage") -> None:
        self.input_tokens += other.input_tokens
        self.cached_input_tokens += other.cached_input_tokens
        self.output_tokens += other.output_tokens


@dataclass
class Task:
    repo_path: str
    issue: str
    test_command: str = "python -m pytest -q -rf -p no:cacheprovider"
    id: str = field(default_factory=lambda: "task_" + uuid.uuid4().hex[:8])


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class Step:
    index: int
    thought: str
    tool_calls: list[ToolCall]
    results: list[str]
    usage: Usage
    latency_ms: int


@dataclass
class TestReport:
    __test__ = False  # not a pytest test class
    exit_code: int
    passed: int
    failed: int
    failed_tests: list[str]
    output_tail: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@dataclass
class TamperFinding:
    path: str
    reason: str


@dataclass
class RunResult:
    run_id: str
    status: RunStatus
    stop_reason: StopReason
    summary: str
    steps: list[Step]
    usage: Usage
    cost_usd: float
    diff: str
    baseline: TestReport | None
    final: TestReport | None
    new_failures: list[str]
    fixed_failures: list[str]
    tamper_findings: list[TamperFinding]
    workspace: str
    elapsed_s: float = 0.0

    @property
    def step_count(self) -> int:
        return len(self.steps)


def new_run_id() -> str:
    return "run_" + uuid.uuid4().hex[:8]


def now() -> float:
    return time.monotonic()
