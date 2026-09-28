"""Execute explicitly planned tool calls without invoking a language model."""

import asyncio
import copy
import inspect
import json
import math
import time
from collections.abc import Callable, Coroutine
from contextlib import AsyncExitStack
from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter
from typing import Any

from jsonschema import Draft202012Validator

from .protocol import BATCH_VALIDATOR, NeedsReasoning, bind_arguments, dependencies


class RetryableToolError(Exception):
    """A tool explicitly reports a transient, safely repeatable failure."""


class UnknownOutcome(Exception):
    """An operation may have taken effect and must not be replayed automatically."""


def _positive(value: float, name: str) -> None:
    if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Coroutine[Any, Any, Any]]
    timeout: float = 10.0
    retries: int = 0
    retry_safe: bool = False
    read_only: bool = True
    resource: str | None = None
    ordered: bool = False

    def __post_init__(self) -> None:
        if not inspect.iscoroutinefunction(self.handler):
            raise ValueError("Tool handlers must be async functions")
        Draft202012Validator.check_schema(self.parameters)
        _positive(self.timeout, "Tool timeout")
        if isinstance(self.retries, bool) or not isinstance(self.retries, int):
            raise ValueError("retries must be an integer")
        if not 0 <= self.retries <= 3 or (self.retries and not self.retry_safe):
            raise ValueError("At most three retries are allowed, only for retry_safe tools")
        if not self.read_only and (self.retry_safe or self.retries):
            raise ValueError("Automatic retries of external writes are not supported in v0.1")
        if self.ordered and not self.resource:
            raise ValueError("An ordered tool must name its shared resource")

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": copy.deepcopy(self.parameters),
            "resource": self.resource,
            "ordered": self.ordered,
            "read_only": self.read_only,
        }


class Engine:
    def __init__(self, tools: list[Tool], *, concurrency: int = 4, timeout: float = 30) -> None:
        if isinstance(concurrency, bool) or not isinstance(concurrency, int) or concurrency < 1:
            raise ValueError("concurrency must be a positive integer")
        self.tools = {tool.name: tool for tool in tools}
        if len(self.tools) != len(tools):
            raise ValueError("Tool names must be unique")
        self.concurrency = concurrency
        _positive(timeout, "Batch timeout")
        self.timeout = timeout
        self._run_lock = asyncio.Lock()
        self._resources = {tool.resource: asyncio.Lock() for tool in tools if tool.resource}
        self._uncertain = False
        self._unfinished: set[asyncio.Task[Any]] = set()

    def _validate(self, batch: dict[str, Any]) -> dict[str, set[str]]:
        BATCH_VALIDATOR.validate(batch)
        actions = batch["actions"]
        ids = {action["id"] for action in actions}
        if len(ids) != len(actions):
            raise ValueError("Action IDs must be unique within a batch")
        graph = {action["id"]: dependencies(action) for action in actions}
        for action in actions:
            if action["tool"] not in self.tools:
                raise ValueError(f"Unknown tool: {action['tool']}")
            if graph[action["id"]] - ids:
                raise ValueError(f"Unknown dependency for {action['id']}")
            args, bindings = action.get("args", {}), action.get("bindings", {})
            if args.keys() & bindings.keys():
                raise ValueError("args and bindings cannot assign the same parameter")
            if not bindings:
                Draft202012Validator(self.tools[action["tool"]].parameters).validate(args)
        try:
            order = tuple(TopologicalSorter(graph).static_order())
        except CycleError as exc:
            raise ValueError("Action dependencies must be acyclic") from exc
        ancestors: dict[str, set[str]] = {}
        for name in order:
            ancestors[name] = set(graph[name])
            for parent in graph[name]:
                ancestors[name].update(ancestors[parent])
        for index, action in enumerate(actions):
            tool = self.tools[action["tool"]]
            for other in actions[index + 1 :]:
                other_tool = self.tools[other["tool"]]
                if (
                    tool.resource
                    and tool.resource == other_tool.resource
                    and (tool.ordered or other_tool.ordered)
                    and action["id"] not in ancestors[other["id"]]
                    and other["id"] not in ancestors[action["id"]]
                ):
                    raise ValueError(f"Explicit ordering required for resource {tool.resource}")
        return graph

    async def execute(self, batch: dict[str, Any]) -> dict[str, Any]:
        async with self._run_lock:
            return await self._execute(batch)

    async def _execute(self, batch: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            if self._uncertain:
                raise ValueError(
                    "Unresolved tool outcome: reconcile outside this engine before reuse"
                )
            batch = json.loads(json.dumps(batch, allow_nan=False))
            self._validate(batch)
        except Exception as exc:
            return {
                "status": "rejected",
                "results": [],
                "error": str(exc),
                "elapsed_s": time.perf_counter() - started,
                "tool_attempts": 0,
            }
        semaphore = asyncio.Semaphore(self.concurrency)
        results: dict[str, Any] = {
            a["id"]: {"id": a["id"], "status": "pending", "attempts": 0, "elapsed_s": 0.0}
            for a in batch["actions"]
        }
        tasks: dict[str, asyncio.Task[None]] = {}

        async def invoke(action: dict[str, Any]) -> None:
            record = results[action["id"]]
            tool = self.tools[action["tool"]]
            action_started = time.perf_counter()
            try:
                for dependency in dependencies(action):
                    await asyncio.shield(tasks[dependency])
                    if results[dependency]["status"] != "succeeded":
                        record.update(status="blocked", error=f"Dependency {dependency} failed")
                        return
                args = bind_arguments(action, results)
                Draft202012Validator(tool.parameters).validate(args)
                async with AsyncExitStack() as stack:
                    if tool.resource:
                        await stack.enter_async_context(self._resources[tool.resource])
                    await stack.enter_async_context(semaphore)
                    if self._uncertain:
                        record.update(status="blocked", error="An earlier outcome is unresolved")
                        return
                    for attempt in range(tool.retries + 1):
                        record["attempts"] += 1
                        try:
                            output = await self._attempt(tool, copy.deepcopy(args))
                            record.update(status="succeeded", output=output)
                            break
                        except (RetryableToolError, TimeoutError):
                            if not tool.retry_safe or attempt == tool.retries:
                                raise
                            await asyncio.sleep(0.05 * (2**attempt))
            except NeedsReasoning as exc:
                record.update(status="needs_reasoning", error=str(exc))
            except UnknownOutcome as exc:
                self._uncertain = True
                record.update(status="outcome_unknown", error=str(exc))
            except asyncio.CancelledError:
                record.update(status="cancelled", error="Batch cancelled or deadline reached")
                raise
            except Exception as exc:
                record.update(status="failed", error=str(exc))
            finally:
                record["elapsed_s"] = time.perf_counter() - action_started

        for action in batch["actions"]:
            tasks[action["id"]] = asyncio.create_task(invoke(action))
        try:
            _, pending = await asyncio.wait(tasks.values(), timeout=self.timeout)
            interrupted = bool(pending)
        except asyncio.CancelledError:
            for task in tasks.values():
                task.cancel()
            await asyncio.gather(*tasks.values(), return_exceptions=True)
            raise
        for task in pending:
            task.cancel()
        await asyncio.gather(*tasks.values(), return_exceptions=True)
        records = list(results.values())
        status = "complete" if all(r["status"] == "succeeded" for r in records) else "partial"
        if interrupted:
            status = "interrupted"
        return {
            "status": status,
            "results": records,
            "elapsed_s": time.perf_counter() - started,
            "tool_attempts": sum(r["attempts"] for r in records),
        }

    async def _stop(self, task: asyncio.Task[Any]) -> bool:
        task.cancel()
        done, _ = await asyncio.wait({task}, timeout=0.1)
        if done:
            if not task.cancelled():
                task.exception()
            return True
        self._unfinished.add(task)

        def consume(finished: asyncio.Task[Any]) -> None:
            self._unfinished.discard(finished)
            if not finished.cancelled():
                finished.exception()

        task.add_done_callback(consume)
        return False

    async def _attempt(self, tool: Tool, args: dict[str, Any]) -> Any:
        task = asyncio.create_task(tool.handler(**args))
        try:
            done, _ = await asyncio.wait({task}, timeout=tool.timeout)
            if not done:
                stopped = await self._stop(task)
                if not stopped or not tool.retry_safe:
                    raise UnknownOutcome(f"{tool.name} timed out; effects may be unresolved")
                raise TimeoutError(f"{tool.name} timed out")
            return json.loads(json.dumps(task.result(), allow_nan=False))
        except asyncio.CancelledError:
            stopped = await self._stop(task)
            if not stopped or not tool.retry_safe:
                raise UnknownOutcome(f"{tool.name} cancelled; effects may be unresolved") from None
            raise
        except (UnknownOutcome, NeedsReasoning):
            raise
        except Exception as exc:
            if not tool.read_only:
                raise UnknownOutcome(
                    f"{tool.name} failed after dispatch; reconcile its outcome"
                ) from exc
            raise
