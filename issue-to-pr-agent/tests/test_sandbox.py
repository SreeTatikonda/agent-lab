import os

from codeagent.sandbox import LocalSandbox


def test_secrets_never_reach_commands(csv_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-leak")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-should-not-leak")
    sb = LocalSandbox(csv_repo, root=tmp_path / "s")
    try:
        out = sb.run("echo key=$ANTHROPIC_API_KEY aws=$AWS_SECRET_ACCESS_KEY home=$HOME").output
        assert "should-not-leak" not in out
        assert f"home={sb.workspace}" in out
    finally:
        sb.close()


def test_agent_edits_never_touch_the_source_repo(sandbox, csv_repo):
    (sandbox.workspace / "billing/export.py").write_text("broken = True\n")
    assert "export_invoices_csv" in (csv_repo / "billing/export.py").read_text()


def test_diff_includes_new_and_changed_files(sandbox):
    (sandbox.workspace / "billing/export.py").write_text("changed = 1\n")
    (sandbox.workspace / "notes.txt").write_text("new file\n")
    diff = sandbox.diff()
    assert "billing/export.py" in diff and "notes.txt" in diff
    assert set(sandbox.changed_files()) == {"billing/export.py", "notes.txt"}


def test_patch_round_trip(sandbox, csv_repo, tmp_path):
    (sandbox.workspace / "billing/export.py").write_text("changed = 1\n")
    (sandbox.workspace / "added.py").write_text("y = 2\n")
    patch = sandbox.diff()
    fresh = LocalSandbox(csv_repo, root=tmp_path / "fresh")
    try:
        fresh.apply_patch(patch)
        assert (fresh.workspace / "billing/export.py").read_text() == "changed = 1\n"
        assert (fresh.workspace / "added.py").read_text() == "y = 2\n"
    finally:
        fresh.close()


def test_close_removes_workspace(csv_repo, tmp_path):
    sb = LocalSandbox(csv_repo, root=tmp_path / "gone")
    root = sb.workspace.parent
    sb.close()
    assert not os.path.exists(root)
