# ReAct-M v0.1 implementation scope

The goal is a public, usable research repository inspired by [ysymyth/ReAct](https://github.com/ysymyth/ReAct): a small implementation, runnable examples, clear experiments and honest claims. The user supplies the multi-action idea and delegates implementation choices. A particular business integration is not the product.

## Required behavior

1. An installable Python 3.11+ package and CLI, with an MIT license.
2. A Reason → Action Batch → Observation loop with a configurable real language-model adapter and an explicitly labeled offline scripted demonstration.
3. A batch accepts multiple tools, literal arguments, references to previous results in that batch and explicit success dependencies. Independent tools run concurrently within a configurable limit.
4. Validate the complete graph before any tool executes. Reject duplicate IDs, missing tools/references and cycles. Validate bound tool arguments before calling that tool.
5. A reference can require exactly one candidate. Zero/multiple candidates return a need for reasoning, instead of silently picking a person or record.
6. Failed or ambiguous branches block their descendants. Unrelated branches continue. Results identify each action and record attempts, status and elapsed time.
7. Async tools declare trusted execution metadata. Shared resources serialize access. Order-sensitive tools additionally require a dependency chain. Retry only explicitly safe tools; side-effect uncertainty must not be treated as a normal retriable error.
8. Bound model rounds, action counts and tool timeouts. Invalid model responses are returned as observations within the round budget. No implicit model calls inside the engine.
9. Include source-based question-answering examples comparable in spirit to ReAct, plus a structured dependency example. Demonstrations run without credentials or external datasets. Provide an optional live, read-only Wikipedia search/read example and an ask command for custom questions; these require network access and a configured model.
10. Provide single-action, independent-parallel and ReAct-M modes. Enforce each mode's restrictions and use identical tool interfaces/data when comparing them.
11. Separate deterministic scheduling measurements from real-model experiments. Report failures, model requests, tokens when supplied by the provider, tool attempts and latency. Do not claim novel parallelism, real-model speedups, SOTA results or reproduced original benchmark scores without evidence.
12. Include a real-model evaluation command and task fixtures with independently specified expected answers. Provide a CI workflow for tests, lint and type checking.

## Public test interfaces

- `Engine.execute(batch)`: actual async tools exercise dependency, concurrency, validation, ambiguity and failure behavior.
- `Agent.run(task)`: a scripted reasoner exercises the complete observation loop and budget/mode restrictions.
- `ChatCompletionsReasoner.decide(...)`: an HTTP transport fixture verifies requests, parsing, token accounting and failures without paid API requests.
- CLI commands: offline demo, comparison and fixture evaluation.

Implementation decisions are delegated by the user; these interfaces concentrate verification on the behavior that matters.

## Deliberate limits

No distributed scheduler, automatic semantic interpretation, arbitrary generated Python execution, general workflow DSL, real refunds, trained Jev router, or guarantee of exactly-once external effects. The first release exposes the small core and documents these limits.

## Completion evidence

An editable installation and wheel build succeed; tests, lint and type checks pass; offline demos and comparison execute from documented commands; actual outputs and methodological limitations are published. A live model result is only marked validated if an actual configured endpoint was used. No credentials are currently configured in the development environment.
