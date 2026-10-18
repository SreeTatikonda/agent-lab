from pathlib import Path

from codeagent.cli import main
from codeagent.evals import load_tasks, run_eval, summarize
from codeagent.llm import ScriptedLLM, call, turn
from codeagent.oracles import ORACLES

TASKS = Path(__file__).resolve().parents[1] / "evals" / "tasks"


def test_every_task_has_an_oracle_and_hidden_tests():
    tasks = load_tasks(TASKS)
    assert {t.id for t in tasks} == set(ORACLES)
    assert all(t.hidden_tests.exists() for t in tasks)


def test_oracles_resolve_every_task():
    rows = run_eval(load_tasks(TASKS), lambda t: ORACLES[t.id]())
    s = summarize(rows)
    assert s["resolve_rate"] == 1.0 and s["tamper_rate"] == 0.0
    assert all(r.hidden_failed == 0 for r in rows)


def test_hidden_tests_catch_a_partial_fix():
    # Fixes only commas by wrapping every field in quotes, which changes plain rows too.
    partial = ScriptedLLM([
        turn("quote everything", call("edit_file", path="billing/export.py",
             old_text='",".join([inv.id, inv.customer_name, f"{inv.total:.2f}"])',
             new_text='",".join(f\'"{v}"\' for v in [inv.id, inv.customer_name, f"{inv.total:.2f}"])')),
        turn("test", call("run_bash", command="python -m pytest -q -rf -p no:cacheprovider")),
        turn("done", call("finish", status="done", summary="quoted")),
    ])
    task = [t for t in load_tasks(TASKS) if t.id == "csv_comma"]
    row = run_eval(task, lambda t: partial)[0]
    assert not row.resolved
    assert row.hidden_failed > 0


def test_cli_eval_writes_json(tmp_path, capsys):
    out = tmp_path / "r.json"
    assert main(["eval", "--tasks", str(TASKS), "--out", str(out)]) == 0
    assert '"resolve_rate": 1.0' in out.read_text()
    assert "csv_comma" in capsys.readouterr().out
