from codeagent.guards import BudgetTracker, RepetitionDetector, mask_old_observations
from codeagent.models import Budgets, Pricing, StopReason, TestReport, Usage
from codeagent.verify import compare, parse_pytest, scan_for_tampering

# ---------------------------------------------------------------- budgets and loops

def test_budget_limits():
    t = BudgetTracker(Budgets(max_steps=3, max_cost_usd=1.0, max_seconds=10))
    assert t.exceeded() is None
    t.steps = 3
    assert t.exceeded() == StopReason.MAX_STEPS
    t.steps, t.cost_usd = 0, 1.5
    assert t.exceeded() == StopReason.MAX_COST
    t.cost_usd, t.elapsed_s = 0, 11
    assert t.exceeded() == StopReason.MAX_TIME


def test_budget_warning_fires_once():
    t = BudgetTracker(Budgets(max_steps=8))
    t.steps = 5
    assert t.warning() is None
    t.steps = 6
    assert "2 steps remain" in t.warning()
    t.steps = 7
    assert t.warning() is None


def test_repetition_detector_warns_then_stops():
    d = RepetitionDetector(warn_at=3, stop_at=4)
    verdicts = [d.record("run_bash", {"command": "pytest"}, "1 failed") for _ in range(4)]
    assert verdicts == [None, None, "warn", "stop"]


def test_same_command_with_new_result_is_progress():
    d = RepetitionDetector(warn_at=2, stop_at=3)
    assert d.record("run_bash", {"command": "pytest"}, "2 failed") is None
    assert d.record("run_bash", {"command": "pytest"}, "1 failed") is None
    assert d.record("run_bash", {"command": "pytest"}, "0 failed") is None


def test_caching_makes_runs_much_cheaper():
    p = Pricing()
    uncached = p.cost(Usage(input_tokens=1_400_000, cached_input_tokens=0, output_tokens=20_000))
    cached = p.cost(Usage(input_tokens=1_400_000, cached_input_tokens=1_260_000, output_tokens=20_000))
    assert round(uncached, 2) == 4.50
    assert round(cached, 2) == 1.10


def _result(text):
    return {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "x", "content": text}]}


def test_masking_keeps_task_and_recent_results():
    messages = [{"role": "user", "content": "the task " + "t" * 1000}]
    for i in range(10):
        messages.append({"role": "assistant", "content": [{"type": "text", "text": "hm"}]})
        messages.append(_result(f"output {i}\n" + "x" * 1000))
    removed = mask_old_observations(messages, keep_recent=3)
    results = [m["content"][0]["content"] for m in messages[1:] if m["role"] == "user"]
    assert removed > 0
    assert all(r.startswith("[masked") for r in results[:7])
    assert all(r.startswith("output") for r in results[7:])
    assert messages[0]["content"].startswith("the task")
    assert "First line was: output 0" in results[0]


def test_masking_is_idempotent():
    messages = [_result("big\n" + "x" * 1000) for _ in range(3)]
    mask_old_observations(messages, keep_recent=1)
    assert mask_old_observations(messages, keep_recent=1) == 0

# ---------------------------------------------------------------- verification

PYTEST_OUT = """..F.
=========================== short test summary info ============================
FAILED tests/test_legacy.py::test_bankers_rounding_legacy - assert 2.67 == 2.68
FAILED tests/test_export.py::test_simple_row - AssertionError
2 failed, 2 passed in 0.03s"""


def test_parse_pytest_summary():
    r = parse_pytest(1, PYTEST_OUT)
    assert (r.passed, r.failed) == (2, 2)
    assert r.failed_tests == ["tests/test_export.py::test_simple_row",
                              "tests/test_legacy.py::test_bankers_rounding_legacy"]


def test_parse_pytest_crash_counts_as_failure():
    r = parse_pytest(2, "ImportError while loading conftest")
    assert r.failed == 1 and r.failed_tests == ["<test run exited with code 2>"]


def test_compare_against_baseline():
    base = TestReport(1, 3, 1, ["legacy"], "")
    final = TestReport(1, 3, 1, ["new_break"], "")
    assert compare(base, final) == (["new_break"], ["legacy"])


TAMPER_DIFF = """diff --git a/tests/test_export.py b/tests/test_export.py
--- a/tests/test_export.py
+++ b/tests/test_export.py
@@ -1,6 +1,7 @@
+@pytest.mark.skip(reason="flaky")
 def test_simple_row():
-    assert out.splitlines()[1] == "A1,Acme,10.00"
+    pass
diff --git a/billing/export.py b/billing/export.py
--- a/billing/export.py
+++ b/billing/export.py
@@ -1,3 +1,6 @@
+    try:
+        x()
+    except Exception:
+        pass
diff --git a/tests/test_legacy.py b/tests/test_legacy.py
deleted file mode 100644
--- a/tests/test_legacy.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def test_bankers_rounding_legacy():
-    assert round_currency(2.675) == 2.68
"""


def test_tamper_scan_finds_reward_hacks():
    reasons = sorted(f.reason.split(":")[0] for f in scan_for_tampering(TAMPER_DIFF))
    assert reasons == ["assertion removed", "broad exception handler added in source",
                       "skip or xfail added", "test file deleted"]


def test_tamper_scan_is_quiet_on_honest_fix():
    honest = """diff --git a/billing/export.py b/billing/export.py
--- a/billing/export.py
+++ b/billing/export.py
@@ -1 +1 @@
-    return ",".join(x)
+    return write_csv(x)
diff --git a/tests/test_export.py b/tests/test_export.py
--- a/tests/test_export.py
+++ b/tests/test_export.py
@@ -1 +1,3 @@
+def test_comma():
+    assert parse(export([row])) == [row]
"""
    assert scan_for_tampering(honest) == []
