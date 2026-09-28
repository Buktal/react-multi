# Design

## Goal

Build a usable open-source research repository in the style of the original ReAct project: a small implementation, clear examples, repeatable experiments, and honest discussion of limitations. The user supplies the multi-action idea and delegates concrete engineering choices.

The first release prioritizes a working core over a general agent framework. The original repository was inspected at commit `6bdb3a1fd38b8188fc7ba4102969fe483df8fdc9`.

## Relationship to ReAct

The original QA notebooks generate one action, call `env.step`, add an observation and reason again. ReAct-M preserves that outer loop but permits a structured batch of actions.

Original `WikiEnv.search` updates a shared current page, and `lookup` consumes that page and advances a cursor. Even searches can therefore interfere within the same environment. This repository's examples use explicit document IDs and immutable fixture data. They are new controlled tasks, not drop-in reproductions of the original benchmarks.

## Modules and interfaces

- `Engine.execute(batch)` validates the entire graph, binds results, schedules tools and returns a BatchReport. It never calls a model.
- `Agent.run(task)` maintains observation history and budgets, requests decisions and handles execution, final answers and user clarification.
- `Reasoner.decide(task, history, tools, mode)` is the model seam. A scripted Adapter makes demos deterministic; an HTTP Adapter calls a configurable real model.
- `Tool` carries its callable, JSON input schema and trusted execution metadata. The model cannot override that metadata.

Execution complexity is concentrated in the Engine. Callers do not manage a scheduler or lock objects. Tests exercise these public interfaces.

## Decisions versus data transfer

A batch may contain steps whose actions are already known and whose arguments can be filled mechanically. A JSON Pointer is a data dependency; choosing which of several people the user intended is a decision dependency.

The runtime only reacts to explicit checks, structural errors and tool signals. It does not interpret arbitrary prose or automatically detect every semantic contradiction. Batch boundaries remain part of the model's responsibility.

The v0.1 binding operator `select: only` is deliberately small. It can establish that there is exactly one candidate, but cannot prove that the candidate is the right one. Arbitrary conditional code, dynamic loops and fan-out stay outside the batch protocol.

## Scheduling and feedback

Independent branches continue when another branch fails. Descendants of an unsuccessful action are blocked. A batch returns once its tasks settle or its deadline interrupts them. There is no overlapping replanning or early streaming observation in v0.1.

Resource locks enforce mutual exclusion, not business ordering. A tool marked `ordered` must share an explicit dependency order with other actions using its resource. This catches the shared-current-page problem instead of hiding it behind a mutex.

## Side effects and trust

Tool functions are trusted async Python code, must cooperate with cancellation, and must not block the event loop. This runtime is not a sandbox and cannot forcibly terminate an arbitrary Python function or undo an external effect.

Only explicitly safe read operations may retry. A timeout without a safe repeatability guarantee, an uncooperative task, or a failed dispatched external write can produce `outcome_unknown`. The Engine then rejects further batches, and the Agent returns `needs_reconciliation`. A host must determine the external outcome before constructing a fresh Engine; restarting blindly is not a recovery procedure.

Locks are in-process and apply only to the same Engine instance. There is no distributed lock, durable execution log, cross-process idempotency, transaction or rollback guarantee. Real refund/payment integrations are intentionally absent.

## Baselines and claims

All three modes use the same Engine, tools and task data. Single mode permits one action per decision; parallel mode permits independent batches; multi mode also permits references and dependencies. Thus differences are not manufactured by giving one mode a better document interface.

Scripted plans validate execution mechanics. They do not show whether a model can generate the plan, whether a larger plan uses more tokens, or whether planning ahead reduces answer accuracy. A real-model evaluation command is included for those questions.

## Deferred work

Jev/retrieval-based tool selection, larger public datasets, original stateful-environment adapters, richer result contracts, streaming replanning and production write recovery are future work. Each needs its own evidence and scope rather than being implicitly promised by the initial release.
