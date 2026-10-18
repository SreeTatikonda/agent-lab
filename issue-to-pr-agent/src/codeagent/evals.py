"""SWE-bench-shaped eval harness for seeded-bug tasks.

Each task has a repo, an issue, and hidden tests the agent never sees. Success means the
hidden tests pass AND nothing that passed at baseline now fails. This mirrors the
fail-to-pass and pass-to-pass checks used by SWE-bench.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .agent import Agent
from .llm import LLM
from .models import Budgets, RunResult, Task
from .verify import run_tests
from .sandbox import LocalSandbox


@dataclass
class EvalTask:
    id: str
    issue: str
    repo: Path
    hidden_tests: Path

    @classmethod
    def load(cls, task_dir: Path) -> "EvalTask":
        meta = json.loads((task_dir / "task.json").read_text())
        return cls(meta["id"], meta["issue"], task_dir / "repo", task_dir / meta["hidden_tests"])


@dataclass
class EvalRow:
    task: str
    resolved: bool
    status: str
    stop_reason: str
    steps: int
    cost_usd: float
    hidden_passed: int
    hidden_failed: int
    new_failures: int
    tampered: bool


def load_tasks(tasks_dir: str | Path) -> list[EvalTask]:
    root = Path(tasks_dir)
    return [EvalTask.load(d) for d in sorted(root.iterdir()) if (d / "task.json").exists()]


def score_hidden(result: RunResult, task: EvalTask) -> tuple[int, int]:
    """Copy hidden tests into the finished workspace and run only them."""
    workspace = Path(result.workspace)
    dest = workspace / "tests" / task.hidden_tests.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(task.hidden_tests, dest)
    sb = LocalSandbox.attach(workspace)
    report = run_tests(sb, f"python -m pytest -q -rf -p no:cacheprovider tests/{dest.name}")
    return report.passed, report.failed


def run_eval(tasks: list[EvalTask], llm_for: Callable[[EvalTask], LLM],
             budgets: Budgets | None = None) -> list[EvalRow]:
    rows: list[EvalRow] = []
    for t in tasks:
        agent = Agent(llm_for(t), budgets=budgets)
        result = agent.run(Task(repo_path=str(t.repo), issue=t.issue, id=t.id))
        try:
            passed, failed = score_hidden(result, t)
        finally:
            shutil.rmtree(Path(result.workspace).parent, ignore_errors=True)
        resolved = (result.status.value == "succeeded" and failed == 0 and passed > 0
                    and not result.new_failures)
        rows.append(EvalRow(t.id, resolved, result.status.value, result.stop_reason.value,
                            result.step_count, result.cost_usd, passed, failed,
                            len(result.new_failures), bool(result.tamper_findings)))
    return rows


def summarize(rows: list[EvalRow]) -> dict:
    n = len(rows) or 1
    resolved = [r for r in rows if r.resolved]
    total_cost = sum(r.cost_usd for r in rows)
    return {
        "tasks": len(rows),
        "resolve_rate": round(len(resolved) / n, 3),
        "cost_per_resolved_usd": round(total_cost / len(resolved), 4) if resolved else None,
        "mean_steps": round(sum(r.steps for r in rows) / n, 1),
        "tamper_rate": round(sum(r.tampered for r in rows) / n, 3),
        "rows": [asdict(r) for r in rows],
    }


def format_table(rows: list[EvalRow]) -> str:
    head = f"{'task':<12} {'resolved':<9} {'stop':<20} {'steps':>5} {'cost':>8} {'hidden':>8} {'tamper':>7}"
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append(f"{r.task:<12} {str(r.resolved):<9} {r.stop_reason:<20} {r.steps:>5} "
                     f"{r.cost_usd:>8.4f} {r.hidden_passed:>3}/{r.hidden_passed + r.hidden_failed:<4} "
                     f"{str(r.tampered):>7}")
    return "\n".join(lines)
