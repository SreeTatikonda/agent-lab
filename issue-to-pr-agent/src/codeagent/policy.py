"""Risk-tiered command policy.

Tier 0 runs freely. Tier 1 needs approval. Tier 2 is always refused.
Pattern matching is a speed bump and an audit signal, not a security boundary.
The real boundary is the sandbox (no secrets, no network in Phase 2).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable


class Tier(IntEnum):
    FREE = 0
    NEEDS_APPROVAL = 1
    BLOCKED = 2


@dataclass(frozen=True)
class Decision:
    tier: Tier
    reason: str


BLOCKED_PATTERNS = [
    (r"\b(curl|wget)\b[^|]*\|\s*(ba|z)?sh\b", "piping a download into a shell"),
    (r"\brm\s+-[a-z]*r[a-z]*f?\s+(/|~|\$HOME)(\s|$)", "recursive delete of root or home"),
    (r"\bgit\s+push\b", "pushing is done by the runtime, never the agent"),
    (r"\b(printenv|env)\b\s*($|\|)", "dumping the environment"),
    (r"\bssh\b|\bscp\b", "remote shells"),
    (r":\(\)\s*\{\s*:\|:&\s*\};:", "fork bomb"),
]

APPROVAL_PATTERNS = [
    (r"\b(curl|wget|nc)\b", "network access"),
    (r"\bpip3?\s+install\b|\bnpm\s+(i|install)\b|\bpoetry\s+add\b", "installing new packages"),
    (r"\.github/|\bci\.ya?ml\b|Dockerfile", "touching CI or build config"),
    (r"\bsudo\b", "privilege escalation"),
]


def classify(command: str) -> Decision:
    for pattern, reason in BLOCKED_PATTERNS:
        if re.search(pattern, command):
            return Decision(Tier.BLOCKED, reason)
    for pattern, reason in APPROVAL_PATTERNS:
        if re.search(pattern, command):
            return Decision(Tier.NEEDS_APPROVAL, reason)
    return Decision(Tier.FREE, "ok")


Approver = Callable[[str, str], bool]


def deny_all(command: str, reason: str) -> bool:
    """Default for unattended runs. Anything risky is refused, and the agent is told why."""
    return False
