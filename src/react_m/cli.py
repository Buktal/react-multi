"""Command-line examples and reproducible experiment entry points."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from .agent import Agent
from .engine import Engine
from .experiments import MODES, compare, load_tasks, run_case, summarize
from .providers import ChatCompletionsReasoner
from .wikipedia import wikipedia_tools


def _save(report: dict[str, Any], output: str | None) -> None:
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _table(rows: list[dict[str, Any]]) -> None:
    print(f"{'scenario':13} {'mode':9} {'success':8} {'decisions':9} {'LLM calls':9} {'seconds':8}")
    for row in rows:
        print(
            f"{row['scenario']:13} {row['mode']:9} {row['success_rate']:<8.0%} "
            f"{row['mean_decisions']:<9.1f} {row['mean_model_calls']:<9.1f} "
            f"{row['median_elapsed_s']:.4f}"
        )


async def _run(args: argparse.Namespace) -> int:
    if args.command == "demo":
        report = await run_case(args.scenario, args.mode)
        print("SCRIPTED DEMONSTRATION - no language model or API request")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        _save(report, args.output)
        return 0 if report["success"] else 1
    if args.command == "compare":
        report = await compare(
            repeats=args.repeats, tool_delay=args.tool_delay, decision_delay=args.decision_delay
        )
        print(report["warning"])
        _table(report["summary"])
        _save(report, args.output)
        return 0 if all(r["success"] for r in report["runs"]) else 1
    if not args.model:
        raise ValueError("Set OPENAI_MODEL or pass --model; no model is selected implicitly")
    api_key = os.environ.get("REACT_M_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    if args.base_url.rstrip("/") == "https://api.openai.com/v1" and not api_key:
        raise ValueError("Set OPENAI_API_KEY locally, or configure a compatible endpoint")
    if args.command == "ask":
        reasoner = ChatCompletionsReasoner(
            args.model, api_key=api_key, base_url=args.base_url, json_mode=not args.no_json_mode
        )
        report = await Agent(Engine(wikipedia_tools(), timeout=60), reasoner, mode=args.mode).run(
            args.question + " Cite the source URLs you used."
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
        _save(report, args.output)
        return 0 if report["status"] in {"finished", "needs_input"} else 1
    if args.repeats < 1:
        raise ValueError("repeats must be positive")
    report = {
        "kind": "live-model-fixtures",
        "model": args.model,
        "warning": "Tiny synthetic fixtures, not an original ReAct benchmark reproduction.",
        "runs": [],
    }
    for _ in range(args.repeats):
        for case in load_tasks():
            for mode in MODES:
                reasoner = ChatCompletionsReasoner(
                    args.model,
                    api_key=api_key,
                    base_url=args.base_url,
                    json_mode=not args.no_json_mode,
                )
                run = await run_case(case["id"], mode, tool_delay=0, reasoner=reasoner)
                report["runs"].append(run)
                _save(report, args.output)
                if run["status"] == "provider_error":
                    print(run["error"])
                    return 1
    report["summary"] = summarize(report["runs"])
    print(report["warning"])
    _table(report["summary"])
    _save(report, args.output)
    return 0 if all(r["success"] for r in report["runs"]) else 1


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="ReAct-M research examples")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Run a labeled offline scripted example")
    demo.add_argument(
        "--scenario", choices=[case["id"] for case in load_tasks()], default="dependency"
    )
    demo.add_argument("--mode", choices=MODES, default="multi")
    demo.add_argument("--output")
    comparison = commands.add_parser("compare", help="Compare scripted execution mechanics")
    comparison.add_argument("--repeats", type=int, default=3)
    comparison.add_argument("--tool-delay", type=float, default=0.02)
    comparison.add_argument("--decision-delay", type=float, default=0.01)
    comparison.add_argument("--output")
    evaluate = commands.add_parser(
        "evaluate", help="Evaluate all modes using a configured real model"
    )
    ask = commands.add_parser("ask", help="Ask a real model a question using live Wikipedia tools")
    ask.add_argument("question")
    ask.add_argument("--mode", choices=MODES, default="multi")
    ask.add_argument("--output", default="results/local/question.json")
    for command in (evaluate, ask):
        command.add_argument("--model", default=os.environ.get("OPENAI_MODEL"))
        command.add_argument(
            "--base-url", default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        )
        command.add_argument("--no-json-mode", action="store_true")
    evaluate.add_argument("--repeats", type=int, default=1)
    evaluate.add_argument("--output", default="results/local/live.json")
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(_run(args)))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
