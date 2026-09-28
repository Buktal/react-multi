"""Small controlled fixtures, clearly separated from live language-model evaluation."""

import asyncio
import copy
import json
import platform
import random
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .agent import Agent, Reasoner, Script, ScriptedReasoner
from .engine import Engine, Tool

DATA = Path(__file__).with_name("data")
MODES = ("single", "parallel", "multi")


def load_tasks() -> list[dict[str, Any]]:
    return json.loads((DATA / "tasks.json").read_text(encoding="utf-8"))


def document_tools(delay: float = 0) -> list[Tool]:
    if delay < 0:
        raise ValueError("Tool delay cannot be negative")
    documents = json.loads((DATA / "documents.json").read_text(encoding="utf-8"))

    async def search(query: str) -> dict[str, Any]:
        await asyncio.sleep(delay)
        return {
            "matches": [
                {"id": key, "title": value["title"]}
                for key, value in documents.items()
                if query.casefold() in value["title"].casefold()
            ]
        }

    async def read(doc_id: str) -> dict[str, Any]:
        await asyncio.sleep(delay)
        if doc_id not in documents:
            raise ValueError(f"Document {doc_id!r} does not exist")
        return copy.deepcopy(documents[doc_id])

    return [
        Tool(
            "search",
            "Search fictional document titles; returns matches with id and title.",
            {
                "type": "object",
                "properties": {"query": {"type": "string", "minLength": 1}},
                "required": ["query"],
                "additionalProperties": False,
            },
            search,
            retry_safe=True,
        ),
        Tool(
            "read",
            "Read a fictional document by ID; returns title, opened (year), and text.",
            {
                "type": "object",
                "properties": {"doc_id": {"type": "string"}},
                "required": ["doc_id"],
                "additionalProperties": False,
            },
            read,
            retry_safe=True,
        ),
    ]


def _execute(*actions: dict[str, Any]) -> dict[str, Any]:
    return {"type": "execute", "actions": list(actions)}


def _observed(history: list[dict[str, Any]]) -> list[Any]:
    return [
        r["output"]
        for h in history
        for r in h["observation"].get("results", [])
        if r["status"] == "succeeded"
    ]


def scripted_plan(scenario: str, mode: str) -> list[Script]:
    """Hand-authored demonstration plans, never presented as model-generated plans."""

    def answer(task: str, history: list[dict[str, Any]], tools: Any, mode: str) -> dict[str, Any]:
        docs = [doc for doc in _observed(history) if "opened" in doc]
        if scenario == "independent":
            value = min(docs, key=lambda doc: doc["opened"])["title"]
        else:
            value = str(docs[-1]["opened"])
        return {"type": "finish", "answer": value}

    if scenario == "independent":
        a = {"id": "a", "tool": "read", "args": {"doc_id": "alder"}}
        b = {"id": "b", "tool": "read", "args": {"doc_id": "birch"}}
        prefix: list[Script] = [_execute(a), _execute(b)] if mode == "single" else [_execute(a, b)]
        return [*prefix, answer]
    if scenario in {"dependency", "ambiguous"}:
        query = "Alder Observatory" if scenario == "dependency" else "Observatory"
        search = {"id": "search", "tool": "search", "args": {"query": query}}
        read = {
            "id": "read",
            "tool": "read",
            "bindings": {
                "doc_id": {
                    "action": "search",
                    "pointer": "/matches",
                    "select": "only",
                    "project": "/id",
                }
            },
        }

        def followup(
            task: str, history: list[dict[str, Any]], tools: Any, mode: str
        ) -> dict[str, Any]:
            matches = _observed(history)[-1]["matches"]
            if len(matches) != 1:
                return {"type": "ask_user", "question": "Which observatory do you mean?"}
            return _execute({"id": "read", "tool": "read", "args": {"doc_id": matches[0]["id"]}})

        if mode == "multi":
            final: Script = (
                answer
                if scenario == "dependency"
                else {"type": "ask_user", "question": "Which observatory do you mean?"}
            )
            return [_execute(search, read), final]
        return [_execute(search), followup, answer]
    if scenario == "failure":
        return [
            _execute({"id": "read", "tool": "read", "args": {"doc_id": "missing"}}),
            {"type": "ask_user", "question": "Please provide a valid document ID."},
        ]
    raise ValueError(f"Unknown scenario: {scenario}")


async def run_case(
    scenario: str,
    mode: str,
    *,
    tool_delay: float = 0.02,
    decision_delay: float = 0.01,
    reasoner: Reasoner | None = None,
) -> dict[str, Any]:
    case = next((case for case in load_tasks() if case["id"] == scenario), None)
    if case is None:
        raise ValueError(f"Unknown scenario: {scenario}")
    chosen = reasoner or ScriptedReasoner(scripted_plan(scenario, mode), delay=decision_delay)
    report = await Agent(Engine(document_tools(tool_delay)), chosen, mode=mode).run(case["task"])
    success = report["status"] == case["expected_status"]
    if "expected_answer" in case:
        success = (
            success
            and str(report["answer"]).strip().casefold() == case["expected_answer"].casefold()
        )
    report.update(scenario=scenario, success=success)
    return report


def summarize(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for scenario in [case["id"] for case in load_tasks()]:
        for mode in MODES:
            group = [r for r in runs if r["scenario"] == scenario and r["mode"] == mode]
            if not group:
                continue
            summaries.append(
                {
                    "scenario": scenario,
                    "mode": mode,
                    "runs": len(group),
                    "success_rate": sum(r["success"] for r in group) / len(group),
                    "median_elapsed_s": statistics.median(r["elapsed_s"] for r in group),
                    "mean_decisions": statistics.mean(r["decision_calls"] for r in group),
                    "mean_model_calls": statistics.mean(r["model_calls"] for r in group),
                    "mean_tool_attempts": statistics.mean(r["tool_attempts"] for r in group),
                }
            )
    return summaries


async def compare(
    *, repeats: int = 3, tool_delay: float = 0.02, decision_delay: float = 0.01, seed: int = 0
) -> dict[str, Any]:
    if repeats < 1 or decision_delay < 0:
        raise ValueError("repeats must be positive and delay nonnegative")
    cases = [(case["id"], mode) for _ in range(repeats) for case in load_tasks() for mode in MODES]
    random.Random(seed).shuffle(cases)
    runs = [
        await run_case(scenario, mode, tool_delay=tool_delay, decision_delay=decision_delay)
        for scenario, mode in cases
    ]
    return {
        "kind": "scripted-mechanics",
        "created_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "platform": platform.system(),
        "configuration": {
            "repeats": repeats,
            "tool_delay_s": tool_delay,
            "decision_delay_s": decision_delay,
            "seed": seed,
        },
        "warning": "Hand-authored plans and simulated delays; not a live-model benchmark.",
        "summary": summarize(runs),
        "runs": runs,
    }
