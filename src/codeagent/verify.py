"""Verification the agent cannot fake.

The runtime runs tests itself, before and after, and compares against the baseline.
It also scans the diff for the classic reward hack of making tests pass by weakening them.
"""
from __future__ import annotations

import re

from .models import TamperFinding, TestReport
from .sandbox import LocalSandbox

_SUMMARY = re.compile(r"(\d+) (passed|failed|error|errors)")
_FAILED_LINE = re.compile(r"^(FAILED|ERROR) (\S+)")


def run_tests(sandbox: LocalSandbox, command: str, timeout: float = 600) -> TestReport:
    result = sandbox.run(command, timeout=timeout, max_lines=400)
    return parse_pytest(result.exit_code, result.output)


def parse_pytest(exit_code: int, output: str) -> TestReport:
    passed = failed = 0
    tail = output.strip().splitlines()[-1] if output.strip() else ""
    for n, kind in _SUMMARY.findall(tail):
        if kind == "passed":
            passed = int(n)
        else:
            failed += int(n)
    failed_tests = sorted({m.group(2) for line in output.splitlines()
                           if (m := _FAILED_LINE.match(line.strip()))})
    if exit_code not in (0, 1) and not failed_tests:
        # collection error, crash, timeout. Treat the whole run as one failure.
        failed_tests = [f"<test run exited with code {exit_code}>"]
        failed = max(failed, 1)
    return TestReport(exit_code, passed, failed, failed_tests, "\n".join(output.splitlines()[-40:]))


def compare(baseline: TestReport, final: TestReport) -> tuple[list[str], list[str]]:
    """New failures are what the agent broke. Fixed failures are pre-existing ones that now pass."""
    before, after = set(baseline.failed_tests), set(final.failed_tests)
    return sorted(after - before), sorted(before - after)


def is_test_path(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return path.startswith("tests/") or "/tests/" in path or name.startswith("test_") or name.endswith("_test.py")


_REMOVED_ASSERT = re.compile(r"^-\s*(assert\b|self\.assert|pytest\.raises)")
_ADDED_SKIP = re.compile(r"^\+.*(@pytest\.mark\.(skip|xfail)|pytest\.skip\(|unittest\.skip|# ?noqa|if False:)")
_BROAD_EXCEPT = re.compile(r"^\+\s*except(\s+(Exception|BaseException))?\s*:\s*(pass)?\s*$")


def scan_for_tampering(diff: str) -> list[TamperFinding]:
    findings: list[TamperFinding] = []
    current = ""
    deleted_files: set[str] = set()
    for line in diff.splitlines():
        if line.startswith("diff --git"):
            current = line.split(" b/", 1)[-1]
            continue
        if line.startswith("deleted file mode") and is_test_path(current):
            deleted_files.add(current)
            findings.append(TamperFinding(current, "test file deleted"))
            continue
        if line.startswith(("+++", "---")) or current in deleted_files:
            continue
        if is_test_path(current):
            if _REMOVED_ASSERT.match(line):
                findings.append(TamperFinding(current, f"assertion removed: {line[1:].strip()[:80]}"))
            if _ADDED_SKIP.match(line):
                findings.append(TamperFinding(current, f"skip or xfail added: {line[1:].strip()[:80]}"))
        elif _BROAD_EXCEPT.match(line):
            findings.append(TamperFinding(current, "broad exception handler added in source"))
    return findings
