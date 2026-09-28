"""The iterative observation loop and an explicitly non-LLM demonstration adapter."""

import asyncio
import copy
import time
from collections.abc import Callable
from typing import Any, Protocol

from jsonschema import Draft202012Validator, ValidationError

from .engine import Engine
from .protocol import BATCH_SCHEMA, dependencies

DECISION_SCHEMA = {
    "oneOf": [
        {
            "type": "object",
            "required": ["type", "actions"],
            "additionalProperties": False,
            "properties": {
                "type": {"const": "execute"},
                "actions": BATCH_SCHEMA["properties"]["actions"],
            },
        },
        {
            "type": "object",
            "required": ["type", "answer"],
            "additionalProperties": False,
            "properties": {"type": {"const": "finish"}, "answer": {"type": "string"}},
        },
        {
            "type": "object",
            "required": ["type", "question"],
            "additionalProperties": False,
            "properties": {
                "type": {"const": "ask_user"},
                "question": {"type": "string", "minLength": 1},
            },
        },
    ],
}


class Reasoner(Protocol):
    is_live: bool
    last_usage: dict[str, int] | None

    async def decide(
        self, task: str, history: list[dict[str, Any]], tools: list[dict[str, Any]], mode: str
    ) -> dict[str, Any]: ...


Script = dict[str, Any] | Callable[..., dict[str, Any]]


class ScriptedReasoner:
    """A supplied sequence of decisions, for deterministic tests and demos only."""

    is_live = False
    last_usage: dict[str, int] | None = None

    def __init__(self, decisions: list[Script], *, delay: float = 0) -> None:
        self.decisions = iter(decisions)
        self.delay = delay

    async def decide(
        self, task: str, history: list[dict[str, Any]], tools: list[dict[str, Any]], mode: str
    ) -> dict[str, Any]:
        await asyncio.sleep(self.delay)
        try:
            decision = next(self.decisions)
        except StopIteration as exc:
            raise ValueError("Scripted decisions exhausted") from exc
        if callable(decision):
            return decision(task, history, tools, mode)
        return copy.deepcopy(decision)


class Agent:
    def __init__(
        self,
        engine: Engine,
        reasoner: Reasoner,
        *,
        mode: str = "multi",
        max_rounds: int = 8,
        max_tool_attempts: int = 128,
    ) -> None:
        if mode not in {"single", "parallel", "multi"}:
            raise ValueError("mode must be single, parallel, or multi")
        if max_rounds < 1 or max_tool_attempts < 1:
            raise ValueError("Budgets must be positive")
        self.engine, self.reasoner, self.mode = engine, reasoner, mode
        self.max_rounds, self.max_tool_attempts = max_rounds, max_tool_attempts

    async def run(self, task: str) -> dict[str, Any]:
        started = time.perf_counter()
        history: list[dict[str, Any]] = []
        report: dict[str, Any] = {
            "status": "budget_exhausted",
            "answer": None,
            "mode": self.mode,
            "backend": "live" if self.reasoner.is_live else "scripted",
            "decision_calls": 0,
            "model_calls": 0,
            "tool_attempts": 0,
            "input_tokens": None,
            "output_tokens": None,
            "usage_complete": True,
            "history": history,
        }
        catalog = [tool.describe() for tool in self.engine.tools.values()]
        for _ in range(self.max_rounds):
            report["decision_calls"] += 1
            report["model_calls"] += int(self.reasoner.is_live)
            decision: dict[str, Any] | None = None
            try:
                decision = await self.reasoner.decide(
                    task, copy.deepcopy(history), catalog, self.mode
                )
                Draft202012Validator(DECISION_SCHEMA).validate(decision)
                if decision["type"] == "finish":
                    report.update(status="finished", answer=decision["answer"])
                    break
                if decision["type"] == "ask_user":
                    report.update(status="needs_input", question=decision["question"])
                    break
                actions = decision["actions"]
                if self.mode == "single" and len(actions) != 1:
                    raise ValueError("single mode permits exactly one action per decision")
                if self.mode in {"single", "parallel"} and any(dependencies(a) for a in actions):
                    raise ValueError(f"{self.mode} mode cannot use intra-batch dependencies")
                reserved = sum(
                    1 + self.engine.tools[a["tool"]].retries
                    for a in actions
                    if a["tool"] in self.engine.tools
                )
                if reserved + report["tool_attempts"] > self.max_tool_attempts:
                    raise ValueError("Batch exceeds remaining tool-attempt budget")
                observation = await self.engine.execute({"actions": actions})
                report["tool_attempts"] += observation["tool_attempts"]
                history.append({"decision": decision, "observation": observation})
                if any(r["status"] == "outcome_unknown" for r in observation["results"]):
                    report["status"] = "needs_reconciliation"
                    break
            except (ValueError, ValidationError) as exc:
                history.append(
                    {"decision": decision, "observation": {"status": "rejected", "error": str(exc)}}
                )
            except Exception as exc:
                report.update(status="provider_error", error=str(exc))
                break
            finally:
                usage = self.reasoner.last_usage
                if self.reasoner.is_live:
                    if usage is None:
                        report["usage_complete"] = False
                    else:
                        for field in ("input_tokens", "output_tokens"):
                            report[field] = (report[field] or 0) + usage.get(field, 0)
        report["elapsed_s"] = time.perf_counter() - started
        return report
