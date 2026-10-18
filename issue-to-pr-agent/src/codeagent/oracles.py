"""Scripted trajectories for the bundled eval tasks.

These are not a model. They are hand-written "ideal runs" used to prove the runtime,
the guards and the eval harness work end to end with zero API cost. Swap in
AnthropicLLM (codeagent eval --model ...) to measure a real model.
"""
from __future__ import annotations

from .llm import ScriptedLLM, call, turn

TEST = "python -m pytest -q -rf -p no:cacheprovider"

CSV_FIXED = '''def export_invoices_csv(invoices):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\\n")
    writer.writerow(HEADER.split(","))
    for inv in invoices:
        writer.writerow([inv.id, inv.customer_name, f"{inv.total:.2f}"])
    return buf.getvalue()'''

CSV_BROKEN = '''def export_invoices_csv(invoices):
    lines = [HEADER]
    for inv in invoices:
        lines.append(",".join([inv.id, inv.customer_name, f"{inv.total:.2f}"]))
    return "\\n".join(lines) + "\\n"'''

CSV_REPRO = '''import csv
import io

from billing.export import Invoice, export_invoices_csv


def test_comma_in_customer_name_is_quoted():
    out = export_invoices_csv([Invoice("A1", "Acme, Inc.", 10)])
    assert list(csv.reader(io.StringIO(out)))[1] == ["A1", "Acme, Inc.", "10.00"]
'''


def csv_comma() -> ScriptedLLM:
    return ScriptedLLM([
        turn("Find the export function named in the issue.",
             call("search_code", pattern=r"def export_invoices_csv")),
        turn("Read it.", call("view_file", path="billing/export.py")),
        turn("Check for an existing csv helper before inventing one.",
             call("search_code", pattern=r"import csv", path_glob="*.py")),
        turn("No helper. Reproduce first with a failing test.",
             call("edit_file", path="tests/test_export_repro.py", old_text="", new_text=CSV_REPRO)),
        turn("Run the reproduction.", call("run_bash", command=f"{TEST} tests/test_export_repro.py")),
        turn("Reproduced. Use the csv module and keep plain rows identical.",
             call("edit_file", path="billing/export.py", old_text=CSV_BROKEN, new_text=CSV_FIXED)),
        turn("Add the imports.",
             call("edit_file", path="billing/export.py", old_text='"""Invoice exports."""\n',
                  new_text='"""Invoice exports."""\nimport csv\nimport io\n')),
        turn("Full suite, compare with baseline.", call("run_bash", command=TEST)),
        turn("Only the pre-existing legacy failure remains.",
             call("finish", status="done",
                  summary="Root cause: rows were built with a plain comma join, so commas and quotes in "
                          "customer names were not escaped. Fix: write rows with csv.writer and a \\n "
                          "line terminator so plain rows are unchanged. Added a regression test. "
                          "test_bankers_rounding_legacy was failing before and is untouched.")),
    ])


def pagination() -> ScriptedLLM:
    return ScriptedLLM([
        turn("Find pagination code.", call("search_code", pattern=r"def (paginate|page_count)")),
        turn("Read it.", call("view_file", path="shop/paging.py")),
        turn("floor drops the partial last page. Use ceiling division.",
             call("edit_file", path="shop/paging.py",
                  old_text="return math.floor(total_items / page_size)",
                  new_text="return math.ceil(total_items / page_size)")),
        turn("Add a regression test.",
             call("edit_file", path="tests/test_paging.py",
                  old_text="def test_first_page():",
                  new_text="def test_partial_last_page():\n    assert paginate(list(range(7)), 2, 5) == [5, 6]\n\n\n"
                           "def test_first_page():")),
        turn("Run tests.", call("run_bash", command=TEST)),
        turn("Green.", call("finish", status="done",
                            summary="page_count used floor, so a partial last page was dropped. Switched to "
                                    "ceil and added a regression test.")),
    ])


def slugify() -> ScriptedLLM:
    return ScriptedLLM([
        turn("Find slugify.", call("search_code", pattern=r"def slugify")),
        turn("Read it.", call("view_file", path="textkit/slug.py")),
        turn("Replace single-space handling with whitespace-and-dash runs, then trim dashes.",
             call("edit_file", path="textkit/slug.py",
                  old_text='    s = s.replace(" ", "-")\n    return s',
                  new_text='    s = re.sub(r"[\\s-]+", "-", s)\n    return s.strip("-")')),
        turn("Run tests.", call("run_bash", command=TEST)),
        turn("Done.", call("finish", status="done",
                           summary="Spaces were replaced one by one, so runs of whitespace became runs of "
                                   "dashes. Collapse whitespace and dashes into one dash and trim the ends.")),
    ])


ORACLES = {"csv_comma": csv_comma, "pagination": pagination, "slugify": slugify}
