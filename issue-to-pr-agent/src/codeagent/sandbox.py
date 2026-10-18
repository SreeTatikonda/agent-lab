"""Local workspace sandbox.

What this is: a throwaway copy of the repo with a scrubbed environment, path
confinement for file tools, per-command timeouts and output truncation.

What this is NOT: a security boundary. Shell commands run as your user on your
machine. For untrusted issues, run the whole agent inside a container or microVM
with networking disabled (see README, Phase 2). The interface below is what a
Docker or Firecracker backend would implement.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules", ".mypy_cache"}

# Only these variables reach commands. API keys, cloud credentials and tokens never do.
SAFE_ENV_KEYS = ("PATH", "LANG", "LC_ALL", "TERM", "TZ", "PYTHONPATH")


class PathEscapeError(ValueError):
    pass


@dataclass
class CommandResult:
    exit_code: int
    output: str
    timed_out: bool
    truncated_lines: int


def truncate_tail(text: str, max_lines: int) -> tuple[str, int]:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text, 0
    dropped = len(lines) - max_lines
    return "\n".join(lines[-max_lines:]), dropped


class LocalSandbox:
    def __init__(self, source_repo: str | Path, root: str | Path | None = None):
        self.source = Path(source_repo).resolve()
        if not self.source.is_dir():
            raise FileNotFoundError(f"repo not found: {self.source}")
        base = Path(root) if root else Path(tempfile.mkdtemp(prefix="codeagent_"))
        self.workspace = (base / "workspace").resolve()
        self._closed = False
        self._copy_repo()
        self._git("init", "-q")
        self._git("add", "-A")
        self._git("-c", "user.name=codeagent", "-c", "user.email=codeagent@localhost",
                  "commit", "-q", "--allow-empty", "-m", "baseline")

    @classmethod
    def attach(cls, workspace: str | Path) -> "LocalSandbox":
        """Wrap an existing workspace (for scoring a finished run) without copying anything."""
        sb = cls.__new__(cls)
        sb.workspace = Path(workspace).resolve()
        sb.source = sb.workspace
        sb._closed = False
        return sb

    # ---- setup -------------------------------------------------------------
    def _copy_repo(self) -> None:
        shutil.copytree(
            self.source,
            self.workspace,
            ignore=shutil.ignore_patterns(*IGNORED_DIRS),
        )

    def _env(self) -> dict[str, str]:
        env = {k: os.environ[k] for k in SAFE_ENV_KEYS if k in os.environ}
        env["HOME"] = str(self.workspace)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["GIT_TERMINAL_PROMPT"] = "0"
        return env

    def _git(self, *args: str) -> str:
        proc = subprocess.run(
            ["git", *args], cwd=self.workspace, env=self._env(),
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
        return proc.stdout

    # ---- paths ---------------------------------------------------------------
    def resolve(self, rel_path: str) -> Path:
        """Resolve a model-supplied path and refuse anything outside the workspace."""
        candidate = (self.workspace / rel_path.lstrip("/")).resolve()
        if candidate != self.workspace and self.workspace not in candidate.parents:
            raise PathEscapeError(f"path escapes the workspace: {rel_path}")
        parts = candidate.relative_to(self.workspace).parts
        if parts and parts[0] == ".git":
            raise PathEscapeError("the .git directory is managed by the runtime")
        return candidate

    def rel(self, path: Path) -> str:
        return str(path.relative_to(self.workspace))

    def iter_files(self, subdir: str = "."):
        start = self.resolve(subdir)
        for dirpath, dirnames, filenames in os.walk(start):
            dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS)
            for name in sorted(filenames):
                yield Path(dirpath) / name

    # ---- commands --------------------------------------------------------------
    def run(self, command: str, timeout: float = 120, max_lines: int = 100) -> CommandResult:
        try:
            proc = subprocess.run(
                command, shell=True, cwd=self.workspace, env=self._env(),
                capture_output=True, text=True, timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
            raw = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
            text, dropped = truncate_tail(raw.strip(), max_lines)
            return CommandResult(proc.returncode, text, False, dropped)
        except subprocess.TimeoutExpired as exc:
            partial = exc.stdout or ""
            if isinstance(partial, bytes):
                partial = partial.decode(errors="replace")
            text, dropped = truncate_tail(partial.strip(), max_lines)
            return CommandResult(124, text, True, dropped)

    # ---- state -------------------------------------------------------------------
    def diff(self) -> str:
        """Unified diff of everything the agent changed, including new files."""
        self._git("add", "-A", "-N")
        return self._git("diff", "--no-color", "HEAD")

    def changed_files(self) -> list[str]:
        self._git("add", "-A", "-N")
        out = self._git("diff", "--name-only", "HEAD")
        return [line for line in out.splitlines() if line.strip()]

    def apply_patch(self, patch: str) -> None:
        if not patch.strip():
            return
        patch_file = self.workspace.parent / "resume.patch"
        patch_file.write_text(patch if patch.endswith("\n") else patch + "\n")
        self._git("apply", "--whitespace=nowarn", str(patch_file))
        patch_file.unlink()

    def close(self) -> None:
        if not self._closed:
            shutil.rmtree(self.workspace.parent, ignore_errors=True)
            self._closed = True
