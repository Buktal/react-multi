# Changelog

## [0.1.0](https://github.com/Buktal/ReAct-M/releases/tag/v0.1.0) — 2026-09-28

- Multi-action ReAct loop with explicit dependencies and JSON Pointer result bindings.
- Concurrent tool execution with resource ordering, deadlines and bounded safe retries.
- Partial results, unique-candidate selection and unknown-outcome handling.
- Configurable Chat Completions model adapter and live Wikipedia search/read tools.
- Offline examples for independent actions, data dependencies, ambiguity and missing evidence.
- Single, parallel and multi execution modes with comparison and model-evaluation commands.
- Installable Python package, command-line interface and runnable notebook.

The included measurements use scripted plans and synthetic documents. Model-based evaluations can be collected with `python -m react_m evaluate`.
