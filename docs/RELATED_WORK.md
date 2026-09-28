# Related work and claim boundaries

Primary sources accessed on 2026-09-28. This note uses the papers' actual abstract pages and the original ReAct repository; it is not a comprehensive literature review.

| Source | What it already establishes | Consequence for ReAct-M |
| --- | --- | --- |
| [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629), Yao et al., ICLR 2023; [code](https://github.com/ysymyth/ReAct) | Interleaving reasoning, actions and observations supports updating plans and handling exceptions. The original QA code calls one action per loop. | Preserve the iterative observation loop. The single-action comparison here is a local baseline, not a claim that every modern ReAct system lacks parallelism. |
| [ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models](https://arxiv.org/abs/2305.18323), Xu et al., 2023 | Separating reasoning from observation-dependent execution reduces repeated prompting. The abstract reports token-efficiency and task results for its own evaluated setup. | Reducing intermediate model calls is established prior work. ReAct-M cannot claim to originate this idea or inherit ReWOO's reported results. |
| [An LLM Compiler for Parallel Function Calling](https://arxiv.org/abs/2312.04511), Kim et al., 2023/2024 | Its abstract describes a function-calling planner, task-fetching unit and parallel executor, with latency/cost/accuracy comparisons to ReAct. | Planner plus dependency-aware execution overlaps strongly with this project. Multi-action planning and parallel scheduling are not novel contributions here. |

## What this repository contributes

A small, inspectable Python implementation for learning and experimenting with action batches: explicit parameter references, an exactly-one selection check, branch failure isolation, conservative handling of unknown outcomes, and comparable single/parallel/multi execution modes. These are implementation and reproducibility choices, not a new reasoning theory.

The useful hypothesis is narrow: **when subsequent actions are already known and need only deterministic parameter transfer, a batch can avoid some intermediate model requests**. When independent calls are the only opportunity, ordinary parallel tool calling should obtain much of the same benefit. When new observations determine what to do next, more reasoning rounds remain necessary.

## What may make it worse

Premature action choices can waste calls or amplify wrong assumptions. Larger plans require more output tokens. A slow independent branch can delay the next reasoning round because v0.1 returns a batch report after its work settles. Stateful tools can eliminate concurrency opportunities. Fewer model calls alone do not establish better task accuracy or lower total cost.

## Evidence required before stronger claims

Use the same model, tool interfaces, task data and meaningful budgets for all modes. Count every model request, invalid output, tool attempt and failed task. Separate a deterministic scheduling demonstration from actual language-model evaluation. Include ambiguous and observation-dependent tasks, not only examples where batching is guaranteed to work. Compare against an independent-parallel baseline, not only a deliberately serial one.

There are no verified live-model benchmark results in the initial development environment because no API credentials are configured. Offline measurements demonstrate execution mechanics only. The project does not reproduce the original HotpotQA, FEVER, ALFWorld or WebShop scores.

## Naming and API provenance

A limited GitHub repository-name search returns unrelated JavaScript projects using `react-m` and related names. This project makes no claim of name uniqueness or affiliation with the ReAct authors, and is not the React JavaScript framework.

The configurable model adapter uses the documented [Chat Completions request interface](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create): `messages`, `max_completion_tokens` and optional JSON-object response mode. JSON-object mode ensures JSON syntax, not compliance with this project's schema; the Agent validates decisions separately. Compatible endpoints can differ, so the model is explicit and JSON mode can be disabled. This adapter is a compatibility choice, not a recommendation that it is the only or newest provider API.
