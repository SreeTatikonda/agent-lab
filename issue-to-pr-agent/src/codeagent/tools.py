"""The agent-computer interface: six tools designed for a model, not a human.

Design rules applied everywhere:
  * every output is capped and says what was left out and how to see more
  * every error says what went wrong and how to recover
  * edits are exact-match, so an edit based on a stale view fails loudly
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any

from .policy import Approver, Tier, classify, deny_all
from .sandbox import LocalSandbox, PathEscapeError

MAX_SEARCH_HITS = 50
MAX_VIEW_LINES = 200
MAX_LIST_ENTRIES = 300
BASH_TAIL_LINES = 100
EDIT_CONTEXT = 3

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "search_code",
        "description": "Regex search across repo files. Returns path:line: text, capped at 50 hits. "
                       "Example {\"pattern\": \"def export_\", \"path_glob\": \"*.py\"}",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path_glob": {"type": "string", "description": "optional fnmatch filter, e.g. *.py"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "list_files",
        "description": "List files under a directory (relative to repo root), capped.",
        "input_schema": {
            "type": "object",
            "properties": {"directory": {"type": "string", "default": "."}},
        },
    },
    {
        "name": "view_file",
        "description": "Show numbered lines of a file, at most 200 per call. Use start/end to page.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start": {"type": "integer", "default": 1},
                "end": {"type": "integer"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace an exact, unique snippet of a file with new text. To create a file, "
                       "pass old_text as an empty string. Fails if old_text is missing or ambiguous.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "run_bash",
        "description": "Run a non-interactive shell command in the repo root. Returns exit code and "
                       "the last 100 lines of output. Default timeout 120s.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "integer", "default": 120},
            },
            "required": ["command"],
        },
    },
    {
        "name": "finish",
        "description": "End the task. Set status to 'done' after verifying with tests, or 'gave_up' "
                       "with what you learned if you cannot complete it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["done", "gave_up"]},
                "summary": {"type": "string"},
            },
            "required": ["status", "summary"],
        },
    },
]


@dataclass
class ToolOutcome:
    text: str
    is_error: bool = False
    finished: bool = False
    finish_status: str = ""
    ran_tests: bool = False
    meta: dict[str, Any] = field(default_factory=dict)


class ToolBox:
    def __init__(self, sandbox: LocalSandbox, approver: Approver = deny_all,
                 test_command: str = "pytest"):
        self.sb = sandbox
        self.approver = approver
        self.test_markers = ("pytest", "unittest", test_command.split()[0])

    def dispatch(self, name: str, args: dict[str, Any]) -> ToolOutcome:
        handler = getattr(self, f"_t_{name}", None)
        if handler is None:
            known = ", ".join(s["name"] for s in TOOL_SPECS)
            return ToolOutcome(f"Unknown tool '{name}'. Available tools are {known}.", is_error=True)
        try:
            return handler(**args)
        except PathEscapeError as exc:
            return ToolOutcome(f"Refused. {exc}. Use paths relative to the repo root.", is_error=True)
        except TypeError as exc:
            return ToolOutcome(f"Bad arguments for {name}. {exc}", is_error=True)

    # ---- search ------------------------------------------------------------------
    def _t_search_code(self, pattern: str, path_glob: str | None = None) -> ToolOutcome:
        try:
            rx = re.compile(pattern)
        except re.error as exc:
            return ToolOutcome(f"Invalid regex ({exc}). Escape special characters or search a literal.",
                               is_error=True)
        hits: list[str] = []
        total = 0
        for path in self.sb.iter_files():
            rel = self.sb.rel(path)
            if path_glob and not _fnmatch(rel, path_glob):
                continue
            try:
                text = path.read_text(errors="strict")
            except (UnicodeDecodeError, OSError):
                continue
            for no, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    total += 1
                    if len(hits) < MAX_SEARCH_HITS:
                        hits.append(f"{rel}:{no}: {line.strip()[:160]}")
        if not hits:
            return ToolOutcome(f"No matches for /{pattern}/. Try a shorter or looser pattern.")
        out = "\n".join(hits)
        if total > len(hits):
            out += f"\n[{total - len(hits)} more matches not shown. Narrow the pattern or add path_glob.]"
        return ToolOutcome(out)

    def _t_list_files(self, directory: str = ".") -> ToolOutcome:
        start = self.sb.resolve(directory)
        if not start.is_dir():
            return ToolOutcome(f"'{directory}' is not a directory.", is_error=True)
        files = [self.sb.rel(p) for p in self.sb.iter_files(directory)]
        shown = files[:MAX_LIST_ENTRIES]
        out = "\n".join(shown) or "(empty)"
        if len(files) > len(shown):
            out += f"\n[{len(files) - len(shown)} more files. List a subdirectory.]"
        return ToolOutcome(out)

    # ---- view and edit -----------------------------------------------------------
    def _t_view_file(self, path: str, start: int = 1, end: int | None = None) -> ToolOutcome:
        target = self.sb.resolve(path)
        if not target.is_file():
            return ToolOutcome(f"No file at '{path}'. Use list_files or search_code to find it.",
                               is_error=True)
        lines = target.read_text(errors="replace").splitlines()
        total = len(lines)
        start = max(1, start)
        end = min(total, end if end else start + MAX_VIEW_LINES - 1, start + MAX_VIEW_LINES - 1)
        body = "\n".join(f"{n:5d}  {lines[n - 1]}" for n in range(start, end + 1))
        header = f"{path} (lines {start}-{end} of {total})"
        footer = ""
        if end < total:
            footer = f"\n[{total - end} more lines. Call view_file with start={end + 1} to continue.]"
        return ToolOutcome(f"{header}\n{body}{footer}")

    def _t_edit_file(self, path: str, old_text: str, new_text: str) -> ToolOutcome:
        target = self.sb.resolve(path)
        if old_text == "":
            if target.exists():
                return ToolOutcome(f"'{path}' already exists. Pass the exact text to replace instead.",
                                   is_error=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(new_text)
            return ToolOutcome(f"Created {path} ({len(new_text.splitlines())} lines).")
        if not target.is_file():
            return ToolOutcome(f"No file at '{path}'. To create it, pass old_text as \"\".", is_error=True)
        content = target.read_text()
        count = content.count(old_text)
        if count == 0:
            hint = _closest_line_hint(content, old_text)
            return ToolOutcome(
                f"old_text not found in {path}. The file may have changed since you viewed it. "
                f"{hint}View the file again and copy the text exactly, including indentation.",
                is_error=True,
            )
        if count > 1:
            return ToolOutcome(
                f"old_text appears {count} times in {path}. Include more surrounding lines so it is unique.",
                is_error=True,
            )
        updated = content.replace(old_text, new_text, 1)
        target.write_text(updated)
        first_line = content[: content.index(old_text)].count("\n") + 1
        new_lines = updated.splitlines()
        lo = max(1, first_line - EDIT_CONTEXT)
        hi = min(len(new_lines), first_line + new_text.count("\n") + EDIT_CONTEXT)
        snippet = "\n".join(f"{n:5d}  {new_lines[n - 1]}" for n in range(lo, hi + 1))
        return ToolOutcome(f"Edited {path}. Lines {lo}-{hi} now read\n{snippet}")

    # ---- shell -------------------------------------------------------------------
    def _t_run_bash(self, command: str, timeout: int = 120) -> ToolOutcome:
        decision = classify(command)
        if decision.tier == Tier.BLOCKED:
            return ToolOutcome(f"Refused by policy ({decision.reason}). Find another way.",
                               is_error=True, meta={"policy": "blocked", "reason": decision.reason})
        if decision.tier == Tier.NEEDS_APPROVAL and not self.approver(command, decision.reason):
            return ToolOutcome(
                f"Not approved ({decision.reason}). Continue without it, or finish with status gave_up "
                f"and explain why it is needed.",
                is_error=True, meta={"policy": "denied", "reason": decision.reason},
            )
        result = self.sb.run(command, timeout=min(timeout, 600), max_lines=BASH_TAIL_LINES)
        parts = [f"exit code {result.exit_code}"]
        if result.timed_out:
            parts.append(f"[timed out after {timeout}s. Avoid interactive or network-bound commands.]")
        if result.truncated_lines:
            parts.append(f"[{result.truncated_lines} earlier lines omitted, showing the tail]")
        parts.append(result.output or "(no output)")
        ran_tests = any(m and m in command for m in self.test_markers)
        return ToolOutcome("\n".join(parts), is_error=result.exit_code != 0 and not ran_tests,
                           ran_tests=ran_tests, meta={"exit_code": result.exit_code})

    def _t_finish(self, status: str, summary: str) -> ToolOutcome:
        if status not in ("done", "gave_up"):
            return ToolOutcome("status must be 'done' or 'gave_up'.", is_error=True)
        return ToolOutcome("Finishing.", finished=True, finish_status=status, meta={"summary": summary})


def _fnmatch(rel: str, glob: str) -> bool:
    import fnmatch
    return fnmatch.fnmatch(rel, glob) or fnmatch.fnmatch(rel.rsplit("/", 1)[-1], glob)


def _closest_line_hint(content: str, old_text: str) -> str:
    first = next((l for l in old_text.splitlines() if l.strip()), "").strip()
    if not first:
        return ""
    lines = content.splitlines()
    match = difflib.get_close_matches(first, [l.strip() for l in lines], n=1, cutoff=0.6)
    if not match:
        return ""
    no = [l.strip() for l in lines].index(match[0]) + 1
    return f"Closest match is line {no}. "
