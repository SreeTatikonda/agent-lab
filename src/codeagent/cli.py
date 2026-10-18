"""Command line entry points.

    codeagent run  --repo PATH --issue "text"  [--model NAME] [--approve]
    codeagent eval [--tasks DIR] [--model NAME]

Without --model, `eval` replays the scripted oracle runs (free, offline).
With --model, it calls the Anthropic API (needs ANTHROPIC_API_KEY).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import Agent
from .evals import format_table, load_tasks, run_eval, summarize
from .models import Budgets, Task
from .policy import deny_all

DEFAULT_TASKS = Path(__file__).resolve().parents[2] / "evals" / "tasks"


def _printer(event: dict) -> None:
    kind = event.get("event")
    if kind == "tool":
        flag = " !" if event.get("error") else ""
        print(f"  step {event['step']:>2}  {event['tool']:<12}{flag} {event['preview']}")
    elif kind == "policy":
        print(f"  policy  {event['decision']}  ({event['reason']})  {event['command']}")
    elif kind in ("baseline", "verifying", "resumed"):
        print(f"[{kind}]")
    elif kind == "done":
        print(f"[done] {event['status']} ({event['reason']}) in {event['steps']} steps, "
              f"USD {event['cost_usd']:.4f}")


def _ask(command: str, reason: str) -> bool:
    answer = input(f"\nApprove `{command}`? ({reason}) [y/N] ").strip().lower()
    return answer == "y"


def cmd_run(args: argparse.Namespace) -> int:
    from .llm import AnthropicLLM
    llm = AnthropicLLM(model=args.model)
    agent = Agent(llm, budgets=Budgets(max_steps=args.max_steps, max_cost_usd=args.max_cost),
                  approver=_ask if args.approve else deny_all,
                  checkpoint_dir=args.checkpoints, on_event=_printer)
    result = agent.run(Task(repo_path=args.repo, issue=args.issue), resume_run_id=args.resume)
    print("\n" + result.summary)
    if result.tamper_findings:
        print("\nREVIEW FLAGS")
        for f in result.tamper_findings:
            print(f"  {f.path}  {f.reason}")
    print("\n" + (result.diff or "(no changes)"))
    print(f"\nworkspace kept at {result.workspace}")
    return 0 if result.status.value == "succeeded" else 1


def cmd_eval(args: argparse.Namespace) -> int:
    tasks = load_tasks(args.tasks)
    if args.model:
        from .llm import AnthropicLLM
        llm_for = lambda t: AnthropicLLM(model=args.model)
    else:
        from .oracles import ORACLES
        llm_for = lambda t: ORACLES[t.id]()
    rows = run_eval(tasks, llm_for, Budgets(max_steps=args.max_steps, max_cost_usd=args.max_cost))
    print(format_table(rows))
    summary = summarize(rows)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="codeagent")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="work on one issue")
    r.add_argument("--repo", required=True)
    r.add_argument("--issue", required=True)
    r.add_argument("--model", default="claude-sonnet-5-5")
    r.add_argument("--max-steps", type=int, default=40)
    r.add_argument("--max-cost", type=float, default=5.0)
    r.add_argument("--approve", action="store_true", help="prompt for risky commands instead of denying")
    r.add_argument("--checkpoints", default=".codeagent/checkpoints")
    r.add_argument("--resume", help="run id to resume from its last checkpoint")
    r.set_defaults(fn=cmd_run)

    e = sub.add_parser("eval", help="run the eval task set")
    e.add_argument("--tasks", default=str(DEFAULT_TASKS))
    e.add_argument("--model", help="real model name. Omit to replay scripted oracle runs")
    e.add_argument("--max-steps", type=int, default=40)
    e.add_argument("--max-cost", type=float, default=5.0)
    e.add_argument("--out", help="write JSON results here")
    e.set_defaults(fn=cmd_eval)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
