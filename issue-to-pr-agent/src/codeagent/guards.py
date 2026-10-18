"""Loop control and context management.

Budgets stop runaways. The repetition detector stops doom loops early.
Observation masking keeps the context from filling with stale tool output.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field

from .models import Budgets, StopReason


@dataclass
class BudgetTracker:
    budgets: Budgets
    steps: int = 0
    cost_usd: float = 0.0
    elapsed_s: float = 0.0
    warned: bool = False

    def exceeded(self) -> StopReason | None:
        if self.steps >= self.budgets.max_steps:
            return StopReason.MAX_STEPS
        if self.cost_usd >= self.budgets.max_cost_usd:
            return StopReason.MAX_COST
        if self.elapsed_s >= self.budgets.max_seconds:
            return StopReason.MAX_TIME
        return None

    def warning(self) -> str | None:
        """One-time nudge near the step budget so the agent wraps up deliberately."""
        if self.warned:
            return None
        if self.steps >= int(self.budgets.max_steps * self.budgets.warn_at_fraction):
            self.warned = True
            left = self.budgets.max_steps - self.steps
            return (f"[runtime] {left} steps remain in your budget. Prioritize verifying your change "
                    f"and calling finish. If you cannot finish, call finish with status gave_up.")
        return None


@dataclass
class RepetitionDetector:
    """Flags the same (tool, input, result) happening again and again.

    Warn at `warn_at` repeats, stop at `stop_at`. Including the result in the key
    matters, because re-running tests after a real edit is progress, not a loop.
    """
    warn_at: int = 3
    stop_at: int = 4
    counts: Counter = field(default_factory=Counter)

    @staticmethod
    def key(tool: str, args: dict, result: str) -> str:
        blob = json.dumps([tool, args, result[-2000:]], sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def record(self, tool: str, args: dict, result: str) -> str | None:
        k = self.key(tool, args, result)
        self.counts[k] += 1
        n = self.counts[k]
        if n >= self.stop_at:
            return "stop"
        if n == self.warn_at:
            return "warn"
        return None


LOOP_WARNING = ("[runtime] You have made the same call with the same result {n} times. "
                "It is not working. Re-read the error, form a different hypothesis, or call finish "
                "with status gave_up and explain what is blocking you.")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def mask_old_observations(messages: list[dict], keep_recent: int = 6, min_chars: int = 400) -> int:
    """Replace bulky tool results older than the last `keep_recent` with a short placeholder.

    The newest results stay intact. The agent can always re-view a file. Returns the number
    of characters removed. Messages before the first assistant turn are never touched, which
    keeps the cached prompt prefix stable.
    """
    result_positions = [
        (i, j)
        for i, m in enumerate(messages)
        if m["role"] == "user" and isinstance(m["content"], list)
        for j, block in enumerate(m["content"])
        if block.get("type") == "tool_result"
    ]
    removed = 0
    for i, j in result_positions[:-keep_recent] if keep_recent else result_positions:
        block = messages[i]["content"][j]
        content = block.get("content", "")
        if isinstance(content, str) and len(content) > min_chars and not content.startswith("[masked"):
            first_line = content.splitlines()[0][:120] if content else ""
            block["content"] = f"[masked old output, {len(content)} chars. First line was: {first_line}]"
            removed += len(content) - len(block["content"])
    return removed
